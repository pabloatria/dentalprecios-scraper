#!/usr/bin/env python3
"""
Generate technical specifications for dental products using Claude AI.

Reads products from Supabase, generates specs via Anthropic API, and writes
them back to the product_specs table.

Usage:
    # Generate specs for top 50 products (by store count)
    ANTHROPIC_API_KEY=sk-... python generate_specs.py

    # Generate for a specific product ID
    ANTHROPIC_API_KEY=sk-... python generate_specs.py --product-id <uuid>

    # Generate for products in a specific category
    ANTHROPIC_API_KEY=sk-... python generate_specs.py --category resinas-compuestas

    # Limit number of products
    ANTHROPIC_API_KEY=sk-... python generate_specs.py --limit 10

    # Dry run (print prompt without calling API)
    python generate_specs.py --dry-run --limit 1
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

# Load env from web/.env.local
ENV_FILE = Path(__file__).parent.parent / "web" / ".env.local"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_supabase_headers(env):
    key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def fetch_products(env, category_slug=None, product_id=None, limit=50):
    """Fetch products that don't have specs yet."""
    url = env["NEXT_PUBLIC_SUPABASE_URL"]
    headers = get_supabase_headers(env)

    if product_id:
        r = requests.get(
            f"{url}/rest/v1/products?id=eq.{product_id}&select=id,name,brand,category:categories(name,slug)",
            headers=headers,
        )
        return r.json()

    # Get ALL existing spec product_ids (paginated)
    existing_ids = set()
    offset = 0
    while True:
        r = requests.get(
            f"{url}/rest/v1/product_specs?select=product_id&limit=1000&offset={offset}",
            headers=headers,
        )
        batch = r.json()
        if not batch:
            break
        existing_ids.update(s["product_id"] for s in batch)
        offset += len(batch)

    # Build base query
    base_query = f"{url}/rest/v1/products?select=id,name,brand,category:categories(name,slug)"
    if category_slug:
        r = requests.get(
            f"{url}/rest/v1/categories?slug=eq.{category_slug}&select=id",
            headers=headers,
        )
        cats = r.json()
        if cats:
            base_query += f"&category_id=eq.{cats[0]['id']}"

    # Paginate through all products
    products = []
    offset = 0
    while len(products) < limit:
        r = requests.get(f"{base_query}&limit=1000&offset={offset}", headers=headers)
        batch = r.json()
        if not batch:
            break
        for p in batch:
            if p["id"] not in existing_ids:
                products.append(p)
                if len(products) >= limit:
                    break
        offset += len(batch)

    return products


SYSTEM_PROMPT = """You are a dental materials expert. Generate precise technical specifications for dental products.

You MUST respond with valid JSON only. No markdown, no explanation, just the JSON object.

The JSON must have these keys:
- composition: Chemical/material composition (string, 1-3 sentences)
- indications: Clinical indications for use (string, comma-separated list)
- contraindications: When NOT to use (string, comma-separated list)
- technique_tips: Practical clinical tips for dentists (string, 2-4 short tips)
- properties: Technical properties as a JSON object. Include ALL applicable properties from the lists below. Use snake_case keys in Spanish. Values must be strings with units.
- compatible_products: Products commonly used together (string, comma-separated)
- comparison_notes: How this product compares to main alternatives (string, 2-3 sentences)

IMPORTANT — Include these properties when applicable to the product type:

MECHANICAL PROPERTIES (resins, composites, cements, ceramics):
- resistencia_compresiva (MPa)
- resistencia_flexural (MPa)
- modulo_elasticidad (GPa)
- dureza_vickers or dureza_knoop (units)
- resistencia_traccion (MPa)
- resistencia_desgaste (description)
- tenacidad_fractura (MPa·m½)

OPTICAL / SHADE PROPERTIES (resins, composites, ceramics, whitening):
- numero_tonos: exact number of available shades (e.g., "31 tonos")
- opciones_tonos: list specific shade names (e.g., "A1, A2, A3, A3.5, B1, B2...")
- opacidad_translucidez: description
- fluorescencia: Si/No
- efecto_camaleon: Si/No

WORKING PROPERTIES (all materials):
- tiempo_trabajo (minutes/seconds)
- tiempo_fraguado or tiempo_curado (minutes/seconds)
- profundidad_curado (mm, for light-cured)
- contraccion_polimerizacion (% volumetric)
- espesor_pelicula (µm, for cements/adhesives)
- viscosidad: description
- radiopacidad: Si/No, or value in mm Al equivalent
- liberacion_fluor: Si/No

PHYSICAL PROPERTIES:
- absorcion_agua (µg/mm³)
- solubilidad (µg/mm³)
- estabilidad_dimensional: description
- densidad (g/cm³)

PRESENTATION:
- presentacion: packaging description (e.g., "Jeringa 4g", "Kit con 8 jeringas")
- contenido: what's included
- vida_util: shelf life
- almacenamiento: storage conditions

Be accurate with real published data. If you know the exact value, include it. If unsure about a specific numeric value, write "consultar ficha técnica" for that field. Use Spanish for all text content."""


def build_prompt(product):
    name = product["name"]
    brand = product.get("brand") or "Unknown"
    category = ""
    if product.get("category"):
        cat = product["category"]
        if isinstance(cat, list) and cat:
            category = cat[0].get("name", "")
        elif isinstance(cat, dict):
            category = cat.get("name", "")

    return f"""Generate technical specifications for this dental product:

Product: {name}
Brand: {brand}
Category: {category}

Respond with JSON only."""


def generate_spec(product, api_key, dry_run=False):
    """Call Claude API to generate specs for a product."""
    prompt = build_prompt(product)

    if dry_run:
        logger.info(f"[DRY RUN] Prompt for {product['name']}:")
        print(f"System: {SYSTEM_PROMPT[:200]}...")
        print(f"User: {prompt}")
        return None

    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2048,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            if r.status_code == 429:
                wait = min(30, 5 * (attempt + 1))
                logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            text = data["content"][0]["text"]

            # Parse JSON from response (handle potential markdown wrapping)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            spec = json.loads(text)
            return spec
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {product['name']}: {e}")
            logger.error(f"Raw response: {text[:500]}")
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error for {product['name']}: {e}, retrying...")
                time.sleep(5)
                continue
            logger.error(f"API error for {product['name']}: {e}")
            return None
    return None


def save_spec(env, product_id, spec):
    """Save generated spec to Supabase."""
    url = env["NEXT_PUBLIC_SUPABASE_URL"]
    headers = get_supabase_headers(env)

    # Ensure properties is a dict
    properties = spec.get("properties", {})
    if isinstance(properties, str):
        try:
            properties = json.loads(properties)
        except json.JSONDecodeError:
            properties = {}

    payload = {
        "product_id": product_id,
        "composition": spec.get("composition", ""),
        "indications": spec.get("indications", ""),
        "contraindications": spec.get("contraindications", ""),
        "technique_tips": spec.get("technique_tips", ""),
        "properties": properties,
        "compatible_products": spec.get("compatible_products", ""),
        "comparison_notes": spec.get("comparison_notes", ""),
        "ai_generated": True,
        "reviewed": False,
    }

    r = requests.post(
        f"{url}/rest/v1/product_specs",
        headers=headers,
        json=payload,
    )

    if r.status_code in (200, 201):
        return True
    else:
        logger.error(f"Failed to save spec: {r.status_code} {r.text[:200]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate dental product specs with AI")
    parser.add_argument("--product-id", help="Generate for a specific product UUID")
    parser.add_argument("--category", help="Category slug to filter by")
    parser.add_argument("--limit", type=int, default=50, help="Max products to process")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    args = parser.parse_args()

    env = load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key and not args.dry_run:
        logger.error("Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    if not env.get("NEXT_PUBLIC_SUPABASE_URL"):
        logger.error("Missing Supabase config in web/.env.local")
        sys.exit(1)

    products = fetch_products(env, args.category, args.product_id, args.limit)
    logger.info(f"Found {len(products)} products to process")

    success = 0
    errors = 0

    for i, product in enumerate(products):
        logger.info(f"[{i+1}/{len(products)}] {product['name']}")

        spec = generate_spec(product, api_key, args.dry_run)
        if spec is None:
            if not args.dry_run:
                errors += 1
            continue

        if save_spec(env, product["id"], spec):
            success += 1
            logger.info(f"  Saved spec for {product['name']}")
        else:
            errors += 1

        # Rate limit: stay under API limits
        if not args.dry_run and i < len(products) - 1:
            time.sleep(3)

    logger.info(f"Done. Success: {success}, Errors: {errors}")


if __name__ == "__main__":
    main()
