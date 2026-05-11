#!/usr/bin/env python3
"""
Auto-categorize uncategorized products.

Strategy:
1. For Shopify suppliers: use collection data to map products to categories
2. For all remaining: use Claude AI to classify based on product name + brand

Usage:
    ANTHROPIC_API_KEY=sk-... python categorize_products.py
    ANTHROPIC_API_KEY=sk-... python categorize_products.py --dry-run
    ANTHROPIC_API_KEY=sk-... python categorize_products.py --limit 100
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

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


def get_headers(env):
    key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def fetch_categories(env):
    """Get all categories as slug->id map."""
    url = env["NEXT_PUBLIC_SUPABASE_URL"]
    r = requests.get(
        f"{url}/rest/v1/categories?select=id,name,slug&parent_id=is.null",
        headers=get_headers(env),
    )
    cats = r.json()
    return {c["slug"]: c["id"] for c in cats}, {c["id"]: c["name"] for c in cats}, {c["name"].lower(): c["id"] for c in cats}


def fetch_uncategorized(env, limit=2000):
    """Get all products with no category, paginated."""
    url = env["NEXT_PUBLIC_SUPABASE_URL"]
    headers = get_headers(env)
    products = []
    offset = 0
    while len(products) < limit:
        r = requests.get(
            f"{url}/rest/v1/products?category_id=is.null&select=id,name,brand&limit=1000&offset={offset}",
            headers=headers,
        )
        batch = r.json()
        if not batch:
            break
        products.extend(batch)
        offset += len(batch)
    return products[:limit]


# Shopify collection -> our category slug mapping
COLLECTION_MAP = {
    # Common Shopify collection handles
    "composites": "resinas-compuestas",
    "resinas": "resinas-compuestas",
    "resinas-compuestas": "resinas-compuestas",
    "composite": "resinas-compuestas",
    "adhesivos": "cementos-adhesivos",
    "cementos": "cementos-adhesivos",
    "cementos-y-adhesivos": "cementos-adhesivos",
    "bonding": "cementos-adhesivos",
    "endodoncia": "endodoncia",
    "endodontics": "endodoncia",
    "limas": "endodoncia",
    "ortodoncia": "ortodoncia",
    "orthodontics": "ortodoncia",
    "cirugia": "cirugia",
    "cirugia-oral": "cirugia",
    "surgical": "cirugia",
    "anestesia": "anestesia",
    "anestesicos": "anestesia",
    "implantes": "implantes",
    "implants": "implantes",
    "instrumental": "instrumental",
    "instrumentos": "instrumental",
    "instruments": "instrumental",
    "fresas": "fresas-diamantes",
    "fresas-y-diamantes": "fresas-diamantes",
    "burs": "fresas-diamantes",
    "impresion": "materiales-impresion",
    "impresiones": "materiales-impresion",
    "impression": "materiales-impresion",
    "alginatos": "materiales-impresion",
    "siliconas": "materiales-impresion",
    "blanqueamiento": "estetica",
    "estetica": "estetica",
    "whitening": "estetica",
    "preventivos": "preventivos",
    "fluor": "preventivos",
    "profilaxis": "preventivos",
    "sellantes": "preventivos",
    "desechables": "desechables",
    "descartables": "desechables",
    "guantes": "control-infecciones-personal",
    "mascarillas": "control-infecciones-personal",
    "bioseguridad": "control-infecciones-personal",
    "desinfeccion": "control-infecciones-clinico",
    "esterilizacion": "control-infecciones-clinico",
    "radiologia": "radiologia",
    "rayos-x": "radiologia",
    "coronas": "coronas-cofias",
    "protesis": "coronas-cofias",
    "provisorios": "coronas-cofias",
    "matrices": "matrices-cunas",
    "cunas": "matrices-cunas",
    "pernos": "pernos-postes",
    "postes": "pernos-postes",
    "retraccion": "materiales-retraccion",
    "hilos-retractores": "materiales-retraccion",
    "goma-dique": "goma-dique",
    "rubber-dam": "goma-dique",
    "ceras": "ceras",
    "laboratorio": "laboratorio",
    "acrilicos": "laboratorio",
    "yesos": "laboratorio",
    "equipamiento": "equipamiento",
    "equipos": "equipamiento",
    "lamparas": "lupas-lamparas",
    "lupas": "lupas-lamparas",
    "piezas-de-mano": "piezas-de-mano",
    "turbinas": "piezas-de-mano",
    "micromotores": "piezas-de-mano",
    "acabado": "acabado-pulido",
    "pulido": "acabado-pulido",
    "acabado-y-pulido": "acabado-pulido",
    "evacuacion": "evacuacion",
    "aspiracion": "evacuacion",
    "jeringas": "jeringas-agujas",
    "agujas": "jeringas-agujas",
    "cad-cam": "cad-cam",
}

# Shopify suppliers and their base URLs
SHOPIFY_SUPPLIERS = {
    "Pareja Lecaros": "https://parejalecaros.cl",
    "SP Dental": "https://spdental.shop",
    "Eksa Dental": "https://eksadental.cl",
    "Gexa Chile": "https://gexachile.cl",
    "BAMS Supplies": "https://www.bamssupplies.com",
    "Naturabel": "https://naturabel.cl",
    "Orbis Dental": "https://www.orbisdental.cl",
    "Dispolab": "https://www.dispolab.cl",
    "AF Chile SPA": "https://afchilespa.cl",
}


def categorize_via_shopify(env, dry_run=False):
    """Use Shopify collection API to categorize products."""
    slug_to_id, _, _ = fetch_categories(env)
    url = env["NEXT_PUBLIC_SUPABASE_URL"]
    headers = get_headers(env)
    total_updated = 0

    for supplier_name, base_url in SHOPIFY_SUPPLIERS.items():
        logger.info(f"Processing Shopify supplier: {supplier_name}")

        # Get supplier ID
        r = requests.get(
            f"{url}/rest/v1/suppliers?name=eq.{requests.utils.quote(supplier_name)}&select=id",
            headers=headers,
        )
        suppliers = r.json()
        if not suppliers:
            logger.warning(f"  Supplier {supplier_name} not found in DB")
            continue
        supplier_id = suppliers[0]["id"]

        # Get collections from Shopify
        try:
            r = requests.get(f"{base_url}/collections.json", timeout=15)
            if r.status_code != 200:
                logger.warning(f"  Could not fetch collections from {base_url}")
                continue
            collections = r.json().get("collections", [])
        except Exception as e:
            logger.warning(f"  Error fetching {base_url}: {e}")
            continue

        for collection in collections:
            handle = collection.get("handle", "")
            category_slug = COLLECTION_MAP.get(handle)
            if not category_slug:
                continue
            category_id = slug_to_id.get(category_slug)
            if not category_id:
                continue

            # Get products in this collection
            try:
                page = 1
                while True:
                    r = requests.get(
                        f"{base_url}/collections/{handle}/products.json?limit=250&page={page}",
                        timeout=15,
                    )
                    if r.status_code != 200:
                        break
                    products = r.json().get("products", [])
                    if not products:
                        break

                    for product in products:
                        title = product.get("title", "")
                        # Find this product in our DB (uncategorized)
                        r2 = requests.get(
                            f"{url}/rest/v1/products?name=eq.{requests.utils.quote(title)}&category_id=is.null&select=id",
                            headers=headers,
                        )
                        matches = r2.json()
                        for match in matches:
                            if dry_run:
                                logger.info(f"  [DRY] {title} -> {category_slug}")
                            else:
                                requests.patch(
                                    f"{url}/rest/v1/products?id=eq.{match['id']}",
                                    headers=headers,
                                    json={"category_id": category_id},
                                )
                            total_updated += 1

                    page += 1
            except Exception as e:
                logger.warning(f"  Error processing collection {handle}: {e}")

    logger.info(f"Shopify categorization: {total_updated} products updated")
    return total_updated


# AI categorization for remaining products
CATEGORIES_LIST = """Available categories (use the exact slug):
- acabado-pulido: Acabado y pulido (polishing discs, strips, finishing burs)
- anestesia: Anestesia (anesthetic cartridges, topical anesthetics)
- cad-cam: CAD CAM (milling blocks, scanners)
- cementos-adhesivos: Cementos y adhesivos (dental cements, bonding agents, adhesives)
- ceras: Ceras (dental waxes)
- cirugia: Cirugía (surgical instruments, sutures, bone grafts)
- control-infecciones-clinico: Control de infecciones clínico (disinfectants, sterilization)
- control-infecciones-personal: Control de infecciones personal (gloves, masks, gowns)
- coronas-cofias: Coronas y cofias (temporary crowns, crown forms)
- desechables: Desechables (disposable cups, bibs, tips)
- endodoncia: Endodoncia (endodontic files, sealers, gutta-percha)
- equipamiento: Equipamiento (dental chairs, units, compressors)
- evacuacion: Evacuación (suction tips, saliva ejectors)
- fresas-diamantes: Fresas y diamantes (burs, diamond burs)
- goma-dique: Goma dique (rubber dam, clamps, frames)
- implantes: Implantes (implant systems, abutments, cover screws)
- instrumental: Instrumental (hand instruments, explorers, mirrors)
- jeringas-agujas: Jeringas y agujas (syringes, needles)
- laboratorio: Laboratorio (acrylics, plasters, articulators)
- lupas-lamparas: Lupas y lámparas (loupes, curing lights, headlamps)
- materiales-impresion: Materiales de impresión (alginate, silicone, polyether)
- materiales-retraccion: Materiales de retracción (retraction cords, paste)
- matrices-cunas: Matrices y cuñas (matrix bands, wedges, sectional matrices)
- miscelaneos: Misceláneos (anything that doesn't fit other categories)
- estetica: Odontología estética (whitening, veneers, cosmetic)
- ortodoncia: Ortodoncia (brackets, wires, elastics)
- pernos-postes: Pernos y postes (fiber posts, prefabricated posts)
- piezas-de-mano: Piezas de mano (handpieces, turbines, contra-angles)
- preventivos: Preventivos (fluoride, sealants, prophylaxis paste)
- radiologia: Radiología (x-ray film, sensors, phosphor plates)
- resinas-compuestas: Resinas compuestas (composite resins, flowable, bulk fill)
- sillones-dentales: Sillones dentales (dental chairs, dental units, portable chairs)
"""

AI_SYSTEM_PROMPT = f"""You are a dental product categorization expert. Given a product name and brand, respond with ONLY the category slug that best fits. No explanation, just the slug.

{CATEGORIES_LIST}

If truly uncertain, respond with: miscelaneos"""


def categorize_via_ai(env, products, dry_run=False):
    """Use Claude to categorize products by name."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not dry_run:
        logger.error("ANTHROPIC_API_KEY required for AI categorization")
        return 0

    slug_to_id, _, _ = fetch_categories(env)
    url = env["NEXT_PUBLIC_SUPABASE_URL"]
    headers = get_headers(env)
    updated = 0
    errors = 0

    # Batch products in groups of 20 for efficiency
    batch_size = 20
    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        product_list = "\n".join(
            f"{j+1}. {p['name']} (Brand: {p.get('brand') or 'Unknown'})"
            for j, p in enumerate(batch)
        )

        prompt = f"""Categorize each product. Respond with ONLY a JSON array of slugs, one per product, in order. Example: ["resinas-compuestas","endodoncia","anestesia"]

Products:
{product_list}"""

        if dry_run:
            logger.info(f"[DRY] Batch {i//batch_size + 1}: {len(batch)} products")
            continue

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
                    "max_tokens": 512,
                    "system": AI_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            r.raise_for_status()
            text = r.json()["content"][0]["text"].strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            slugs = json.loads(text)

            for p, slug in zip(batch, slugs):
                cat_id = slug_to_id.get(slug)
                if cat_id:
                    requests.patch(
                        f"{url}/rest/v1/products?id=eq.{p['id']}",
                        headers=headers,
                        json={"category_id": cat_id},
                    )
                    updated += 1
                else:
                    logger.warning(f"  Unknown slug '{slug}' for {p['name']}")
                    errors += 1

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"  Parse error on batch {i//batch_size + 1}: {e}")
            errors += len(batch)
        except Exception as e:
            logger.error(f"  API error on batch {i//batch_size + 1}: {e}")
            errors += len(batch)

        time.sleep(0.5)

    logger.info(f"AI categorization: {updated} updated, {errors} errors")
    return updated


def main():
    parser = argparse.ArgumentParser(description="Auto-categorize dental products")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--skip-shopify", action="store_true", help="Skip Shopify collection mapping")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI categorization")
    args = parser.parse_args()

    env = load_env()

    # Step 1: Shopify collection mapping
    shopify_count = 0
    if not args.skip_shopify:
        logger.info("=== Step 1: Shopify collection mapping ===")
        shopify_count = categorize_via_shopify(env, args.dry_run)

    # Step 2: AI categorization for remaining
    if not args.skip_ai:
        logger.info("=== Step 2: AI categorization for remaining ===")
        remaining = fetch_uncategorized(env, args.limit)
        logger.info(f"Found {len(remaining)} uncategorized products remaining")
        if remaining:
            ai_count = categorize_via_ai(env, remaining, args.dry_run)
        else:
            ai_count = 0
            logger.info("No uncategorized products remaining!")

    logger.info(f"=== Done. Shopify: {shopify_count}, AI: {ai_count if not args.skip_ai else 'skipped'} ===")


if __name__ == "__main__":
    main()
