"""
Seed script: Insert catalog-only entries for major implant and aesthetic brands
that don't have publicly scrapeable pricing in Chile.

These products get price=0 entries, which the UI shows as "Consultar precio"
with a "Contactar proveedor" button linking to the brand/distributor page.

Run once: python3 seed_catalog_brands.py
"""
from __future__ import annotations

import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Brand catalog definitions
# ──────────────────────────────────────────────────────────────

CATALOG_BRANDS = [
    # ─── DENTAL IMPLANT BRANDS ───
    {
        "supplier_name": "Straumann",
        "website_url": "https://www.straumann.com/cl/es/home.html",
        "category": "implantologia",
        "products": [
            {"name": "Straumann BLX Implant", "brand": "Straumann"},
            {"name": "Straumann BLT Implant (Bone Level Tapered)", "brand": "Straumann"},
            {"name": "Straumann TLX Implant", "brand": "Straumann"},
            {"name": "Straumann Standard Plus Implant (SLA)", "brand": "Straumann"},
            {"name": "Straumann Pro Arch", "brand": "Straumann"},
            {"name": "Straumann Variobase Abutment", "brand": "Straumann"},
        ],
    },
    {
        "supplier_name": "Nobel Biocare",
        "website_url": "https://www.nobelbiocare.com/es-cl",
        "category": "implantologia",
        "products": [
            {"name": "Nobel Biocare NobelActive Implant", "brand": "Nobel Biocare"},
            {"name": "Nobel Biocare NobelParallel CC Implant", "brand": "Nobel Biocare"},
            {"name": "Nobel Biocare NobelReplace Conical Connection", "brand": "Nobel Biocare"},
            {"name": "Nobel Biocare All-on-4 Treatment Concept", "brand": "Nobel Biocare"},
            {"name": "Nobel Biocare Zygoma Implant", "brand": "Nobel Biocare"},
        ],
    },
    {
        "supplier_name": "Osstem",
        "website_url": "https://www.osstem.com",
        "category": "implantologia",
        "products": [
            {"name": "Osstem TS III Implant", "brand": "Osstem"},
            {"name": "Osstem TS IV Implant", "brand": "Osstem"},
            {"name": "Osstem SS III Implant", "brand": "Osstem"},
            {"name": "Osstem MS Implant (Mini)", "brand": "Osstem"},
        ],
    },
    {
        "supplier_name": "Neodent",
        "website_url": "https://www.neodent.com.br",
        "category": "implantologia",
        "products": [
            {"name": "Neodent Grand Morse Helix Implant", "brand": "Neodent"},
            {"name": "Neodent Titamax EX Implant", "brand": "Neodent"},
            {"name": "Neodent Zi Ceramic Implant", "brand": "Neodent"},
        ],
    },
    {
        "supplier_name": "Hiossen",
        "website_url": "https://www.hiossen.com",
        "category": "implantologia",
        "products": [
            {"name": "Hiossen ET III Implant", "brand": "Hiossen"},
            {"name": "Hiossen ET V Implant", "brand": "Hiossen"},
            {"name": "Hiossen ETII Bio Implant", "brand": "Hiossen"},
        ],
    },
    {
        "supplier_name": "MIS Implants",
        "website_url": "https://www.mis-implants.com",
        "category": "implantologia",
        "products": [
            {"name": "MIS C1 Conical Connection Implant", "brand": "MIS"},
            {"name": "MIS V3 Implant", "brand": "MIS"},
            {"name": "MIS Seven Implant", "brand": "MIS"},
        ],
    },
    {
        "supplier_name": "BioHorizons",
        "website_url": "https://www.biohorizons.com",
        "category": "implantologia",
        "products": [
            {"name": "BioHorizons Tapered Internal Implant", "brand": "BioHorizons"},
            {"name": "BioHorizons Tapered Pro Implant", "brand": "BioHorizons"},
            {"name": "BioHorizons Laser-Lok Implant", "brand": "BioHorizons"},
        ],
    },
    {
        "supplier_name": "Megagen",
        "website_url": "https://www.megagen.com",
        "category": "implantologia",
        "products": [
            {"name": "Megagen AnyRidge Implant", "brand": "Megagen"},
            {"name": "Megagen AnyOne Implant", "brand": "Megagen"},
            {"name": "Megagen BlueDiamond Implant", "brand": "Megagen"},
        ],
    },
    {
        "supplier_name": "Zimmer Biomet Dental",
        "website_url": "https://www.zimmerbiometdental.com",
        "category": "implantologia",
        "products": [
            {"name": "Zimmer Biomet T3 Implant", "brand": "Zimmer Biomet"},
            {"name": "Zimmer Biomet Tapered Screw-Vent Implant", "brand": "Zimmer Biomet"},
            {"name": "Zimmer Biomet Trabecular Metal Implant", "brand": "Zimmer Biomet"},
        ],
    },
    {
        "supplier_name": "Adin Implants",
        "website_url": "https://www.adin-implants.com",
        "category": "implantologia",
        "products": [
            {"name": "Adin CloseFit Implant", "brand": "Adin"},
            {"name": "Adin Touareg-S Implant", "brand": "Adin"},
        ],
    },
    {
        "supplier_name": "Bicon",
        "website_url": "https://www.bicon.com",
        "category": "implantologia",
        "products": [
            {"name": "Bicon Short Implant", "brand": "Bicon"},
            {"name": "Bicon MAX 2.5 Implant", "brand": "Bicon"},
        ],
    },
    {
        "supplier_name": "S.I.N. Implant System",
        "website_url": "https://www.sinimplantsystem.com.br",
        "category": "implantologia",
        "products": [
            {"name": "S.I.N. Strong SW Implant", "brand": "S.I.N."},
            {"name": "S.I.N. Tryon Implant", "brand": "S.I.N."},
        ],
    },
    {
        "supplier_name": "BTI Biotechnology Institute",
        "website_url": "https://bti-biotechnologyinstitute.com",
        "category": "implantologia",
        "products": [
            {"name": "BTI Interna Universal Implant", "brand": "BTI"},
            {"name": "BTI Core Implant", "brand": "BTI"},
            {"name": "BTI PRGF-Endoret Kit", "brand": "BTI"},
        ],
    },
    {
        "supplier_name": "Dentsply Sirona Implants",
        "website_url": "https://www.dentsplysirona.com/es-cl",
        "category": "implantologia",
        "products": [
            {"name": "Dentsply Astra Tech EV Implant", "brand": "Dentsply Sirona"},
            {"name": "Dentsply Ankylos C/X Implant", "brand": "Dentsply Sirona"},
            {"name": "Dentsply XiVE Implant", "brand": "Dentsply Sirona"},
        ],
    },

    # ─── AESTHETIC / FACIAL BRANDS ───
    {
        "supplier_name": "Galderma",
        "website_url": "https://www.galderma.com/cl",
        "category": "estetica",
        "products": [
            {"name": "Restylane (Ácido Hialurónico)", "brand": "Galderma"},
            {"name": "Restylane Lyft", "brand": "Galderma"},
            {"name": "Restylane Defyne", "brand": "Galderma"},
            {"name": "Sculptra (Ác. Poli-L-Láctico)", "brand": "Galderma"},
            {"name": "Dysport (Toxina Botulínica)", "brand": "Galderma"},
        ],
    },
    {
        "supplier_name": "Merz Aesthetics",
        "website_url": "https://www.merzaesthetics.com",
        "category": "estetica",
        "products": [
            {"name": "Belotero Balance (Ácido Hialurónico)", "brand": "Merz"},
            {"name": "Belotero Volume", "brand": "Merz"},
            {"name": "Belotero Intense", "brand": "Merz"},
            {"name": "Radiesse (Hidroxilapatita de Calcio)", "brand": "Merz"},
            {"name": "Xeomin (Toxina Botulínica)", "brand": "Merz"},
        ],
    },
    {
        "supplier_name": "Allergan / AbbVie Aesthetics",
        "website_url": "https://www.allergan.com",
        "category": "estetica",
        "products": [
            {"name": "Juvederm Ultra (Ácido Hialurónico)", "brand": "Allergan"},
            {"name": "Juvederm Voluma", "brand": "Allergan"},
            {"name": "Juvederm Volbella", "brand": "Allergan"},
            {"name": "Juvederm Volift", "brand": "Allergan"},
            {"name": "Botox (Toxina Botulínica Tipo A)", "brand": "Allergan"},
        ],
    },
    {
        "supplier_name": "Hugel",
        "website_url": "https://www.hugel.co.kr/en",
        "category": "estetica",
        "products": [
            {"name": "Letybo (Toxina Botulínica)", "brand": "Hugel"},
            {"name": "The Chaeum Premium (Ácido Hialurónico)", "brand": "Hugel"},
        ],
    },
    {
        "supplier_name": "Croma-Pharma",
        "website_url": "https://www.croma.at",
        "category": "estetica",
        "products": [
            {"name": "Princess Filler (Ácido Hialurónico)", "brand": "Croma-Pharma"},
            {"name": "Princess Volume", "brand": "Croma-Pharma"},
            {"name": "Saypha Rich", "brand": "Croma-Pharma"},
        ],
    },
    {
        "supplier_name": "Teoxane",
        "website_url": "https://www.teoxane.com",
        "category": "estetica",
        "products": [
            {"name": "Teosyal RHA (Ácido Hialurónico)", "brand": "Teoxane"},
            {"name": "Teosyal Ultra Deep", "brand": "Teoxane"},
            {"name": "Teosyal PureSense Redensity I", "brand": "Teoxane"},
            {"name": "Teosyal PureSense Redensity II", "brand": "Teoxane"},
        ],
    },
]


def main():
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        logger.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    sb = create_client(url, key)

    total_suppliers = 0
    total_products = 0
    total_prices = 0

    for brand_data in CATALOG_BRANDS:
        supplier_name = brand_data["supplier_name"]
        website_url = brand_data["website_url"]
        category_slug = brand_data["category"]
        products = brand_data["products"]

        # Get or create supplier
        result = sb.table("suppliers").select("id").eq("name", supplier_name).execute()
        if result.data:
            supplier_id = result.data[0]["id"]
        else:
            result = sb.table("suppliers").insert({
                "name": supplier_name,
                "website_url": website_url,
                "active": True,
            }).execute()
            if not result.data:
                logger.error(f"Failed to create supplier: {supplier_name}")
                continue
            supplier_id = result.data[0]["id"]
            total_suppliers += 1
            logger.info(f"Created supplier: {supplier_name}")

        # Get category ID
        cat_result = sb.table("categories").select("id").eq("slug", category_slug).execute()
        category_id = cat_result.data[0]["id"] if cat_result.data else None

        for product_data in products:
            product_name = product_data["name"]
            brand = product_data.get("brand", "")

            # Get or create product
            result = sb.table("products").select("id").eq("name", product_name).execute()
            if result.data:
                product_id = result.data[0]["id"]
            else:
                insert_data = {"name": product_name}
                if brand:
                    insert_data["brand"] = brand
                if category_id:
                    insert_data["category_id"] = category_id

                result = sb.table("products").insert(insert_data).execute()
                if not result.data:
                    logger.warning(f"Failed to create product: {product_name}")
                    continue
                product_id = result.data[0]["id"]
                total_products += 1

            # Insert catalog-only price (price=0)
            try:
                sb.table("prices").insert({
                    "product_id": product_id,
                    "supplier_id": supplier_id,
                    "price": 0,
                    "product_url": website_url,
                    "in_stock": True,
                }).execute()
                total_prices += 1
            except Exception as e:
                logger.warning(f"Price insert failed for {product_name}: {e}")

        print(f"  {supplier_name}: {len(products)} products seeded")

    print(f"\n=== SEED COMPLETE ===")
    print(f"  New suppliers: {total_suppliers}")
    print(f"  New products: {total_products}")
    print(f"  Prices inserted: {total_prices}")


if __name__ == "__main__":
    main()
