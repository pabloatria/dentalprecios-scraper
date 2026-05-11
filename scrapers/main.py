from __future__ import annotations

import os
import re
import sys
import time
import unicodedata
import logging
from collections import defaultdict
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client


# Saline-product detection pattern, used by refine_category_for_product().
# Synced with the DB-side backfill regex in migration
# backfill_suero_fisiologico_categorization (2026-05-08).
# Input is accent-stripped via _strip_accents() before matching, so the
# pattern can use plain ASCII without caring about NFC/NFD variations or
# composed-vs-decomposed accented characters.
_SALINE_PATTERN = re.compile(
    r'(suero\s+fisiolog'
    r'|suero\s+salino'
    r'|solucion\s+salina\s+fisiolog'
    r'|nacl\s*0[.,]\s*9'
    r'|cloruro\s+de\s+sodio\s+(?:al\s+)?0[.,]\s*9)',
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    """Remove combining accent marks: Solución -> Solucion, NaCl0,9 -> NaCl0,9."""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )


def retry_supabase(fn, max_retries=3, delay=5):
    """Retry a Supabase operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Supabase error (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(delay * (2 ** attempt))

# Add the scrapers directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from matchers import tokenize, are_same_product

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Import all scrapers
# ──────────────────────────────────────────────────────────────

# Existing scrapers
from suppliers.dentsolutions import DentsolutionsScraper
from suppliers.dental_macaya import DentalMacayaScraper

# WooCommerce scrapers (generic)
from suppliers.techdent import TechdentScraper
from suppliers.clandent import ClandentScraper
from suppliers.dentalamerica import DentalamericaScraper
from suppliers.afchilespa import AfchilespaScraper

# Shopify scrapers (JSON API)
from suppliers.eksadental import EksaDentalScraper
from suppliers.spdental import SpDentalScraper
from suppliers.tubotiquin import TubotiquinScraper
from suppliers.geerdink import GeerdinkScraper

# Specialty platform scrapers
from suppliers.orthomedical import OrthomedicalScraper
from suppliers.dipromed import DipromedScraper
from suppliers.biotechchile import BiotechChileScraper

# Previously Cloudflare-blocked sites (now using cloudscraper)
from suppliers.superdental_cf import SuperDentalCFScraper
from suppliers.mayordent import MayordentScraper
from suppliers.dentobal import DentobalScraper
from suppliers.siromax import SiromaxScraper

# Additional WC Store API scrapers
from suppliers.gipfel import GipfelScraper

# Aesthetic suppliers (Shopify)
from suppliers.bamssupplies import BamsSuppliesScraper
from suppliers.dispolab import DispolabScraper
from suppliers.naturabel import NaturabelScraper

# Aesthetic suppliers (WooCommerce)
from suppliers.flamamed import FlamamedScraper

# Catalog-only suppliers (no prices, contact for pricing)
from suppliers.torregal import TorregalScraper

# Additional dental suppliers
from suppliers.tresdental import TresDentalScraper
from suppliers.orbisdental import OrbisDentalScraper

# New dental suppliers (batch 2)
from suppliers.dentosmed import DentosmedScraper
from suppliers.expressdent import ExpressDentScraper
from suppliers.nexodental import NexoDentalScraper
from suppliers.gexachile import GexaChileScraper
from suppliers.denteeth import DenteethScraper

# New dental suppliers (batch 3)
from suppliers.biomateriales import BiomaterialesScraper
from suppliers.dentalmaxspa import DentalMaxSpaScraper
from suppliers.parejalecaros import ParejaLecarosScraper
from suppliers.dentallaval import DentalLavalScraper

# New dental suppliers (batch 4)
from suppliers.tiendadentinet import TiendaDentinetScraper
from suppliers.depodental import DepodentalScraper

# New dental suppliers (batch 5)
from suppliers.dentalprime import DentalPrimeScraper

# New dental suppliers (batch 6)
from suppliers.gacchile import GacChileScraper
from suppliers.dentalpluschile import DentalPlusChileScraper

# New dental suppliers (batch 7)
from suppliers.surdent import SurdentScraper

# New dental suppliers (batch 8)
from suppliers.schudent import SchudentScraper

# New dental suppliers (batch 9)
from suppliers.dentica import DenticaScraper

# New dental suppliers (batch 10)
from suppliers.odontoimport import OdontoimportScraper

# New dental suppliers (batch 11)
from suppliers.larense import LarenseScraper
from suppliers.dentalalameda import DentalAlamedaScraper
from suppliers.dentaltech import DentalTechScraper
from suppliers.dentalstore import DentalStoreScraper
from suppliers.dentalimport import DentalImportScraper
from suppliers.dentaldepot import DentalDepotScraper

# New dental suppliers (batch 13)
from suppliers.exprodental import ExproDentalScraper

# New dental suppliers (batch 14)
from suppliers.dentalguzman import DentalGuzmanScraper

# New dental suppliers (batch 15)
from suppliers.ccdental import CCDentalScraper

# Brand direct stores (batch 16)
from suppliers.curaprox import CuraproxScraper

# ──────────────────────────────────────────────────────────────
# Scraper registry
# ──────────────────────────────────────────────────────────────

SCRAPERS = [
    # Working scrapers (can fetch via HTTP)
    DentsolutionsScraper(),        # Jumpseller
    DentalMacayaScraper(),         # WooCommerce
    TechdentScraper(),             # WooCommerce + Astra
    ClandentScraper(),             # WooCommerce
    DentalamericaScraper(),        # WooCommerce
    AfchilespaScraper(),           # WooCommerce
    EksaDentalScraper(),           # Shopify JSON API
    SpDentalScraper(),             # Shopify JSON API
    OrthomedicalScraper(),         # WC Store API
    DipromedScraper(),             # PrestaShop
    BiotechChileScraper(),         # Odoo 18

    # Previously blocked (now using cloudscraper)
    # SuperDentalCFScraper(),       # DISABLED 2026-04-15: superdental.cl homepage
    #                               # returns 403, /wp-json/ 404, only /?rest_route=
    #                               # serves Indonesian gambling spam. Domain looks
    #                               # hijacked or taken down. Re-enable only after
    #                               # manual confirmation that the real dental site
    #                               # is back.
    MayordentScraper(),             # WC Store API + cloudscraper
    DentobalScraper(),              # Shopify JSON API + cloudscraper
    SiromaxScraper(),               # WC Store API + cloudscraper

    # Additional suppliers
    GipfelScraper(),                # WC Store API
    BamsSuppliesScraper(),          # Shopify JSON API (aesthetic supplies)
    DispolabScraper(),              # Shopify JSON API (aesthetic supplies)
    NaturabelScraper(),             # Shopify JSON API (aesthetic supplies)
    FlamamedScraper(),              # WC Store API (aesthetic supplies)

    # Catalog-only (no prices)
    TorregalScraper(),               # WP REST API (aesthetic equipment, catalog-only)

    # Additional dental suppliers
    TresDentalScraper(),             # WC Store API (3D printers, resins, scanners)
    OrbisDentalScraper(),            # Shopify JSON API (orthodontics, mini-implants)

    # New dental suppliers (batch 2)
    DentosmedScraper(),              # WooCommerce (dental supplies, instruments)
    ExpressDentScraper(),            # WooCommerce (dental consumables, equipment)
    NexoDentalScraper(),             # WooCommerce (dental supplies, lab materials)
    GexaChileScraper(),              # Shopify JSON API (equipment, orthodontics, digital)
    DenteethScraper(),               # WooCommerce (instruments, lab, orthodontics)

    # New dental suppliers (batch 3)
    BiomaterialesScraper(),            # Jumpseller (bone grafts, membranes, surgical)
    DentalMaxSpaScraper(),             # WC Store API (bone grafts, membranes, instruments)
    ParejaLecarosScraper(),            # Shopify JSON API (composites, endodontics, lab)
    DentalLavalScraper(),              # Shopify JSON API (Zeiss, W&H, EMS, equipment)

    # New dental suppliers (batch 4)
    TiendaDentinetScraper(),             # Jumpseller (composites, endodontics, surgery, etc.)
    DepodentalScraper(),                 # WC Store API (composites, instruments, orthodontics)

    # New dental suppliers (batch 5)
    DentalPrimeScraper(),                    # WooCommerce (tissue adhesives, sutures)

    # New dental suppliers (batch 6)
    GacChileScraper(),                       # WooCommerce (orthodontic supplies)
    DentalPlusChileScraper(),                # PrestaShop (dental supplies, instruments)

    # New dental suppliers (batch 7)
    SurdentScraper(),                            # WC Store API (Kuraray distributor, equipment, materials)
    SchudentScraper(),                           # WooCommerce HTML (SprintRay distributor, CAD/CAM blocks)

    # New dental suppliers (batch 9)
    DenticaScraper(),                                # WC Store API (general dental supplies)

    # New dental suppliers (batch 10)
    OdontoimportScraper(),                               # ASP.NET HTML + JSON-LD (sitemap discovery, ~1000 products)

    # New dental suppliers (batch 11)
    LarenseScraper(),                                        # WC Store API (general dental supplies)
    DentalAlamedaScraper(),                                  # WC Store API (general dental supplies)
    DentalTechScraper(),                                     # WC Store API (general dental supplies)
    DentalStoreScraper(),                                    # WC Store API (general dental supplies)
    DentalImportScraper(),                                   # WC Store API (general dental supplies)

    # New dental suppliers (batch 12)
    DentalDepotScraper(),                                        # Shopify JSON API (dental consumables, ~145 products)

    # New dental suppliers (batch 13)
    ExproDentalScraper(),                                            # Custom PHP HTML (~1800 dental products)

    # New dental suppliers (batch 14)
    DentalGuzmanScraper(),                                               # WooCommerce HTML (~159 dental products)

    # New dental suppliers (batch 15)
    CCDentalScraper(),                                                       # Jumpseller HTML (~280 endodontics products)

    # Brand direct stores (batch 16)
    CuraproxScraper(),                                                           # PrestaShop (toothbrushes, toothpaste, interdental, oral hygiene)

    # Medical commodity distributors (batch 17, added 2026-05-07)
    # Cover the dental clinic procurement gap: guantes estériles, suero, agujas
    # hipodérmicas, jeringas, gasas, mascarillas, alcohol/povidona — items the
    # dental specialty distributors don't reliably carry.
    TubotiquinScraper(),                                                             # Shopify JSON API (medical commodities, full EPP + wound care)
    GeerdinkScraper(),                                                               # Shopify JSON API (medical disposables, wound care, jeringas)
]


def ensure_supplier(supabase, scraper) -> Optional[str]:
    """Get or create supplier in database. Returns supplier_id."""
    result = retry_supabase(
        lambda: supabase.table("suppliers").select("id").eq("name", scraper.name).execute()
    )
    if result.data:
        return result.data[0]["id"]

    # Create supplier
    result = retry_supabase(
        lambda: supabase.table("suppliers").insert({
            "name": scraper.name,
            "website_url": scraper.website_url,
            "active": True,
        }).execute()
    )

    if result.data:
        logger.info(f"Created supplier: {scraper.name}")
        return result.data[0]["id"]

    logger.error(f"Failed to create supplier: {scraper.name}")
    return None


class ProductCache:
    """In-memory product cache with inverted token index for fast fuzzy lookup.

    Preloads all products at startup so ensure_product() can do in-memory
    fuzzy matching instead of hitting the database for every candidate.
    """

    def __init__(self):
        self.products: list[dict] = []       # [{id, name, image_url, brand}]
        self.name_to_idx: dict[str, int] = {}  # exact name → index
        self.token_index: dict[str, set[int]] = defaultdict(set)

    def load(self, supabase):
        """Load all products from the database into memory."""
        all_products = []
        page_size = 1000
        offset = 0

        while True:
            result = supabase.table("products") \
                .select("id, name, image_url, brand") \
                .range(offset, offset + page_size - 1) \
                .execute()

            if not result.data:
                break
            all_products.extend(result.data)
            if len(result.data) < page_size:
                break
            offset += page_size

        self.products = all_products
        self._rebuild_indexes()
        logger.info(f"ProductCache loaded {len(self.products)} products")

    def _rebuild_indexes(self):
        """Rebuild exact-name and token indexes from self.products."""
        self.name_to_idx.clear()
        self.token_index.clear()
        for i, p in enumerate(self.products):
            self.name_to_idx[p["name"]] = i
            for token in tokenize(p["name"]):
                self.token_index[token].add(i)

    def exact_match(self, name: str) -> Optional[dict]:
        """Find product by exact name. Returns product dict or None."""
        idx = self.name_to_idx.get(name)
        if idx is not None:
            return self.products[idx]
        return None

    def fuzzy_match(self, name: str) -> Optional[dict]:
        """Find a product that fuzzy-matches this name.

        Uses the inverted token index to find candidates quickly,
        then checks with are_same_product() for confirmation.
        Only candidates sharing at least 2 tokens are checked.
        """
        tokens = tokenize(name)
        if not tokens:
            return None

        # Count how many tokens each candidate shares
        candidate_counts: dict[int, int] = defaultdict(int)
        for token in tokens:
            for idx in self.token_index.get(token, set()):
                candidate_counts[idx] += 1

        # Check candidates with at least 2 shared tokens, best first
        for idx, shared in sorted(candidate_counts.items(),
                                   key=lambda x: x[1], reverse=True):
            if shared < 2:
                break
            if are_same_product(name, self.products[idx]["name"]):
                return self.products[idx]

        return None

    def add(self, product: dict):
        """Add a newly created product to the cache."""
        idx = len(self.products)
        self.products.append(product)
        self.name_to_idx[product["name"]] = idx
        for token in tokenize(product["name"]):
            self.token_index[token].add(idx)


# Global product cache (initialized in main)
_product_cache: Optional[ProductCache] = None


def ensure_product(supabase, name: str, category_slug: str = None,
                    image_url: str = None, brand: str = None) -> Optional[str]:
    """Get or create product in database. Returns product_id.

    Uses a three-tier lookup:
    1. Exact name match (in-memory cache)
    2. Fuzzy name match via are_same_product() (in-memory cache)
    3. Create new product (database INSERT + cache update)

    Updates image_url and brand if provided and currently missing.
    """
    global _product_cache

    # --- Tier 1: Exact match (in-memory) ---
    cached = _product_cache.exact_match(name) if _product_cache else None
    if cached:
        product_id = cached["id"]
        updates = {}
        if image_url and not cached.get("image_url"):
            updates["image_url"] = image_url
        if brand and not cached.get("brand"):
            updates["brand"] = brand
        if updates:
            try:
                supabase.table("products").update(updates).eq("id", product_id).execute()
                cached.update(updates)  # keep cache in sync
            except Exception as e:
                logger.warning(f"Failed to update product metadata: {e}")
        return product_id

    # --- Tier 2: Fuzzy match (in-memory) ---
    if _product_cache:
        fuzzy = _product_cache.fuzzy_match(name)
        if fuzzy:
            logger.debug(f"Fuzzy match: '{name}' → '{fuzzy['name']}'")
            product_id = fuzzy["id"]
            updates = {}
            if image_url and not fuzzy.get("image_url"):
                updates["image_url"] = image_url
            if brand and not fuzzy.get("brand"):
                updates["brand"] = brand
            if updates:
                try:
                    supabase.table("products").update(updates).eq("id", product_id).execute()
                    fuzzy.update(updates)
                except Exception as e:
                    logger.warning(f"Failed to update product metadata: {e}")
            return product_id

    # --- Tier 3: Create new product ---
    product_data = {"name": name}

    if image_url:
        product_data["image_url"] = image_url
    if brand:
        product_data["brand"] = brand

    # Persist pack_size when the name makes it explicit (e.g. "2 Jeringas").
    # NULL when unknown — never guess. Enables pack-aware comparison in UI
    # and prevents the 1-pack vs 2-pack price-spread bug from recurring.
    try:
        from matchers import extract_pack_count
        pack_size = extract_pack_count(name)
        if pack_size is not None:
            product_data["pack_size"] = pack_size
    except Exception as e:
        logger.warning(f"pack_size extraction failed for '{name}': {e}")

    # Try to link to a category
    if category_slug:
        cat_result = supabase.table("categories").select("id").eq("slug", category_slug).execute()
        if cat_result.data:
            product_data["category_id"] = cat_result.data[0]["id"]

    result = supabase.table("products").insert(product_data).execute()
    if result.data:
        new_product = result.data[0]
        # Add to cache so subsequent items in this run can match it
        if _product_cache:
            _product_cache.add({
                "id": new_product["id"],
                "name": name,
                "image_url": image_url,
                "brand": brand,
            })
        return new_product["id"]

    return None


# ──────────────────────────────────────────────────────────────
# Category mapping: supplier category → our category slug
# ──────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    # ──────────────────────────────────────────────────────────────
    # 30 standardized categories (slugs):
    #   acabado-pulido, anestesia, cad-cam, cementos-adhesivos, ceras,
    #   cirugia, control-infecciones-clinico, control-infecciones-personal,
    #   coronas-cofias, desechables, endodoncia, equipamiento, estetica,
    #   evacuacion, fresas-diamantes, goma-dique, implantes, instrumental,
    #   jeringas-agujas, laboratorio, lupas-lamparas, materiales-impresion,
    #   materiales-retraccion, matrices-cunas, miscelaneos, ortodoncia,
    #   pernos-postes, piezas-de-mano, preventivos, radiologia,
    #   resinas-3d, resinas-compuestas
    # ──────────────────────────────────────────────────────────────

    # SuperDental
    "adhesion-y-restauracion": "resinas-compuestas",
    "anestesicos-y-agujas": "anestesia",
    "barnices-y-fluor": "preventivos",
    "blanqueamiento-y-barreras": "estetica",
    "desechables": "desechables",
    "desinfeccion-y-bioseguridad": "control-infecciones-clinico",
    "endodoncia": "endodoncia",
    "equipamiento": "equipamiento",
    "fresas": "fresas-diamantes",
    "higiene-oral": "preventivos",
    "impresion-y-rehabilitacion": "materiales-impresion",
    "instrumental": "instrumental",
    "laboratorio": "laboratorio",
    "ortodoncia": "ortodoncia",
    "periodoncia-y-cirugia": "cirugia",
    "protesis-y-carillas": "coronas-cofias",
    "radiologia": "radiologia",

    # Dentsolutions (Jumpseller)
    "anestesia": "anestesia",
    "blanqueamiento": "estetica",
    "operatoria": "cementos-adhesivos",
    "prevencion": "preventivos",

    # Techdent
    "accesorios-para-clinica-dental": "equipamiento",
    "insumos-dentales/desechables-para-dentistas": "desechables",
    "insumos-dentales/insumos-instrumental-dental": "instrumental",
    "insumos-dentales/fresas-dentales": "fresas-diamantes",
    "equipamiento-dental/equipamiento-cirugia-dental": "equipamiento",
    "equipamiento-dental/compresores-y-bombas-de-succion": "equipamiento",
    "equipamiento-dental/esterilizacion-y-desinfeccion": "control-infecciones-clinico",
    "equipamiento-dental/imagen-digital": "radiologia",
    "equipamiento-dental/mobiliario-clinico-dental": "equipamiento",
    "equipamiento-dental/sillones-dentales": "equipamiento",
    "equipamiento-dental/repuestos-y-mantenimiento-de-equipos-dentales": "equipamiento",
    "laboratorio/equipos-para-laboratorio": "laboratorio",

    # Dipromed (PrestaShop)
    "10-instrumentos-medicos": "instrumental",
    "59-guantes": "control-infecciones-personal",
    "109-conos": "desechables",
    "125-rehabilitacion": "laboratorio",
    "151-esterilizacion": "control-infecciones-clinico",

    # Shopify product types (eksadental, spdental)
    "repuestos": "equipamiento",
    "turbinas": "piezas-de-mano",
    "implantologia": "implantes",
    "resinas": "resinas-compuestas",

    # Gipfel (WC Store API)
    "cirugia": "cirugia",
    "dental": None,
    "todos": None,

    # BAMS Supplies (Shopify - aesthetic)
    "ácido hialurónico": "estetica",
    "bioestimulador": "estetica",
    "regeneradores celulares": "estetica",
    "hilos de bioestimulación": "estetica",
    "hilos de tracción": "estetica",
    "hilos de relleno": "estetica",
    "toxina botulínica": "estetica",
    "mesoterapia y peeling": "estetica",
    "lipolíticos": "estetica",
    "cánulas": "estetica",
    "micro agujas": "estetica",
    "otros": None,

    # Dispolab (Shopify - aesthetic)
    "inyectable": "estetica",
    "hilo estimulante": "estetica",
    "dispositivo medico": "estetica",
    "serum": None,
    "crema": None,
    "crema antiedad": None,
    "shampoo": None,
    "shampoo acondicionador": None,
    "solucion micelar": None,
    "antitranspirante": None,
    "lamina silicona": None,
    "gel silicona": None,
    "barra silicona": None,

    # Naturabel (Shopify - aesthetic)
    "meline": "estetica",

    # Flamamed (WC Store API - aesthetic)
    "acido-hialuronico": "estetica",
    "profhilo": "estetica",
    "exosomas": "estetica",
    "hilos-mesotrax": "estetica",
    "bcn-cocktails": "estetica",
    "bcn-peels": "estetica",
    "bcn-classics": "estetica",
    "bcn-advance": "estetica",
    "bcn-prebiotics": "estetica",
    "cebelia": "estetica",
    "agujas-mesoterapia": "estetica",
    "agujas": "estetica",
    "agujas-hipodermicas": "estetica",
    "canulas": "estetica",
    "canulas-agujas-y-canulas": "estetica",
    "insumos": None,

    # Torregal (WP REST API - aesthetic equipment)
    "estetica-equipos": "estetica",

    # 3Dental (WC Store API - CAD/CAM, 3D printing)
    "impresoras-3d-odontologicas": "cad-cam",
    "impresoras-3d": "cad-cam",
    "resinas-dentales": "resinas-3d",
    "termoformadoras": "laboratorio",
    "termoformadoras-laminas": "laboratorio",
    "scanners": "cad-cam",
    "scanners-intraoral": "cad-cam",
    "scanners-de-mesa": "cad-cam",
    "pre-y-pos-proceso": "cad-cam",
    "insumos-de-laboratorio": "laboratorio",
    "filamento-para-impresion-3d": "resinas-3d",
    "higiene-protesica": "preventivos",
    "ofertas": None,
    "ofertas-cyber": None,
    "sin-categorizar": None,
    "scheu": "laboratorio",
    "asiga": "cad-cam",

    # Orbis Dental (Shopify - orthodontics)
    "productos ortodoncia": "ortodoncia",
    "kits": "ortodoncia",
    "disyuntores": "ortodoncia",
    "mini implantes marpe": "ortodoncia",
    "mini implantes extra alveolares": "ortodoncia",
    "mini implantes interradiculares": "ortodoncia",

    # Dentosmed (WooCommerce)
    "1-dental/22-cirugia-2": "cirugia",
    "1-dental/23-desechables-2": "desechables",
    "1-dental/24-esterilizacion-2": "control-infecciones-clinico",
    "1-dental/33-periodoncia-2": "cirugia",
    "1-dental/25-radiologia-2": "radiologia",
    "1-dental/26-ortodoncia-2": "ortodoncia",
    "1-dental/21-restauracion-2": "cementos-adhesivos",
    "1-dental/27-endodoncia-2": "endodoncia",
    "1-dental/15-implantes-2": "implantes",
    "1-dental/34-laboratorio": "laboratorio",
    "1-dental/32-impresion-2": "materiales-impresion",
    "1-dental/37-instrumental-2": "instrumental",
    "1-dental/28-rotatorios-2": "piezas-de-mano",
    "1-dental/6-accesorios-2": "equipamiento",
    "1-dental/31-higiene-bucal-2": "preventivos",
    "1-dental/29-aire-y-succion-2": "evacuacion",
    "1-dental/41-ortopedia": "ortodoncia",

    # ExpressDent (WooCommerce)
    "esterilizacion": "control-infecciones-clinico",
    "odontopediatria": "preventivos",
    "rehabilitacion-oral": "laboratorio",
    "periodoncia": "cirugia",
    "flujo-digital": "cad-cam",

    # NexoDental (WooCommerce)
    "equipos": "equipamiento",
    "fresas-y-pulido": "fresas-diamantes",
    "impresion": "materiales-impresion",
    "instrumental-y-accesorios": "instrumental",
    "limpieza-e-higiene-bucal": "preventivos",
    "radiografia": "radiologia",

    # Gexa Chile (Shopify)
    "laboratorio dental": "laboratorio",
    "odontología digital": "cad-cam",
    "equipamiento dental": "equipamiento",

    # Denteeth (WooCommerce)
    "laboratorio-2": "laboratorio",
    "restauracion": "cementos-adhesivos",
    "descartables": "desechables",
    "rotatorio": "piezas-de-mano",

    # DentalMaxSpa (WC Store API)
    "rellenos": "implantes",
    "membranas": "implantes",
    "tejidos-blandos": "implantes",
    "raspadores": "cirugia",
    "regeneracion": "implantes",
    "bienair": "piezas-de-mano",

    # Dental Prime (WooCommerce)
    "adhesivos": "cementos-adhesivos",
    "suturas": "cirugia",

    # GAC Chile (WooCommerce - orthodontics)
    "ali": "ortodoncia",
    "anclaje": "ortodoncia",
    "arcos-y-alambres": "ortodoncia",
    "auxiliares": "ortodoncia",
    "bandas": "ortodoncia",
    "brackets": "ortodoncia",
    "consulta-y-laboratorio": "laboratorio",
    "elastomericos": "ortodoncia",
    "instrumentos": "instrumental",
    "ortopedia-dental": "ortodoncia",
    "tubos": "ortodoncia",

    # Surdent (WC Store API - Kuraray distributor)
    "material-dental": None,  # too broad, sub-categories below
    "materiales-rehabilitacion": "laboratorio",
    "composite": "resinas-compuestas",
    "cementos": "cementos-adhesivos",
    "acabado-y-pulido": "acabado-pulido",
    "estetica-y-rehabilitacion": "estetica",
    "fresas-fresarios-kits": "fresas-diamantes",
    "lampara-fotocurado": "lupas-lamparas",
    "papeles-articulares": "miscelaneos",
    "elastomeros": "materiales-impresion",
    "siliconas": "materiales-impresion",
    "otros-materiales": None,
    "profilaxis": "preventivos",
    "sillones-dentales": "equipamiento",
    "unidades-dentales": "equipamiento",
    "autoclaves": "control-infecciones-clinico",
    "esterilizacion-y-autoclave": "control-infecciones-clinico",
    "ultrasonidos-piezoelectricos": "piezas-de-mano",
    "instrumental-rotatorio": "piezas-de-mano",
    "insertos": "piezas-de-mano",
    "radiologia-intraoral": "radiologia",
    "proteccion-radiologica-y-otros": "radiologia",
    "elementos-proteccion-personal-epp": "control-infecciones-personal",
    "instrumental-ortodoncia": "ortodoncia",
    "equipos-laboratorio": "laboratorio",
    "vacio-aspiracion": "evacuacion",
    "bombas-de-vacio": "equipamiento",
    "aire": "equipamiento",
    "muebles-odontologicos": "equipamiento",

    # Dental Plus Chile (PrestaShop)
    "4-clinica-dental": "desechables",
    "171-higiene-dental": "preventivos",
    "6-endodoncia": "endodoncia",
    "3-carbide": "fresas-diamantes",
    "5-diamante": "fresas-diamantes",
    "7-equipamiento": "equipamiento",
    "8-instrumental": "instrumental",
    "9-insumos-medicos": "desechables",
    "10-laboratorio": "laboratorio",
    "11-instr-rotatorio": "piezas-de-mano",

    # Schudent (WooCommerce HTML - shop page scrape)
    # All products come as "tienda" since we scrape /tienda/
    # Products are mixed (CAD/CAM, instruments, resins) — map to general
    "tienda": None,  # Will be categorized by product name matching

    # Curaprox Chile (PrestaShop - oral hygiene brand store)
    "cepillos-manuales": "preventivos",
    "cepillos-electricos": "preventivos",
    "cepillos-infantiles": "preventivos",
    "cepillos-especializados": "preventivos",
    "pasta-dental": "preventivos",
    "pasta-dental-infantil": "preventivos",
    "pasta-colutorio-especializado": "preventivos",
    "cepillos-interdentales": "preventivos",
    "cepillos-interdentales-especializados": "preventivos",
    "hilo-dental": "preventivos",
    "chupetes-mordedores": "preventivos",

    # Tubotiquin (Shopify) - medical commodities for dental clinic procurement.
    # Keys are lowercased product_type values from /products.json.
    "insumos médicos": "desechables",
    "jeringas luer lock": "jeringas-agujas",
    "jeringas de insulina": "jeringas-agujas",
    "protección personal": "control-infecciones-personal",
    "gasas y apósitos": "desechables",
    "apósito antimicrobiano": "desechables",
    "alcohol 70": "control-infecciones-clinico",
    "desinfectantes": "control-infecciones-clinico",
    "cinta adhesiva": "desechables",
    "cuidado de heridas": "desechables",
    "medición y control": "equipamiento",
    "protector cutáneo": "desechables",
    "removedor adhesivos médicos": "desechables",
    "parche hidrocoloide": "desechables",
    # "instrumentos médicos" from tubotiquin is generic surgical disposables
    # (scissors, hemostats, kits), NOT dental instrumental. Leave uncategorized
    # to avoid polluting the dental "instrumental" page; specific items get
    # picked up by name-based filter views or stay in /buscar discovery.
    "instrumentos médicos": None,
    "artículos de infusión": "jeringas-agujas",
    "oxigenoterapia": "equipamiento",
    "emergencias médicas": None,
    "ostomía": None,
    "accesorios para ostomía": None,
    "ortesis": None,
    "ortopedia": None,
    "medias de compresión": None,
    "suplementos alimenticios": None,
    "entrenamiento y simulación": None,
    "mobiliario": None,
    "botiquines": None,
    "inmovilizador de hombro": None,

    # Geerdink (Shopify) - medical disposables, wound care, jeringas.
    "insumos desechables": "desechables",
    "curación de heridas": "desechables",
    "jeringas y agujas": "jeringas-agujas",
    "geles ultrasonido": "equipamiento",
    "limpieza": "control-infecciones-clinico",
    "cremas hidratantes": None,
    "labiales hidratantes": None,
    "terapia compresiva": None,
    "lesiones y ortopedia": None,
    "diabetes": None,
    "kits y packs": None,
    "productos geerdink": None,
    "suplementos": None,
    "cuidado personal": None,
}


def check_and_record_restock(supabase, product_id, supplier_id, new_in_stock):
    """If product went from out-of-stock to in-stock, record a restock event."""
    if not new_in_stock:
        return  # Only care about items coming back in stock

    # Get the most recent previous price for this product+supplier
    result = supabase.table("prices") \
        .select("in_stock") \
        .eq("product_id", product_id) \
        .eq("supplier_id", supplier_id) \
        .order("scraped_at", desc=True) \
        .limit(1) \
        .execute()

    if not result.data:
        return  # First time seeing this product at this supplier — not a restock

    prev_in_stock = result.data[0]["in_stock"]
    if prev_in_stock:
        return  # Was already in stock — no change

    # Restock detected! Record the event
    logger.info(f"RESTOCK DETECTED: product={product_id} supplier={supplier_id}")
    try:
        supabase.table("restock_events").insert({
            "product_id": product_id,
            "supplier_id": supplier_id,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to record restock event: {e}")


def detect_price_drop(supabase, product_id, supplier_id, current_price, product_url=""):
    """
    Fallback offer detection: if price dropped >10% vs previous scrape
    for the SAME product URL, return the previous price as original_price.
    Requires same product_url to avoid false positives from dedup collisions
    (e.g. two different products sharing one product_id).
    Caps at 50% max discount to filter data anomalies.
    Returns previous price int if drop is 10-50%, else None.
    """
    query = supabase.table("prices") \
        .select("price, product_url") \
        .eq("product_id", product_id) \
        .eq("supplier_id", supplier_id) \
        .order("scraped_at", desc=True) \
        .limit(1)

    result = query.execute()

    if not result.data:
        return None  # First time seeing this product

    prev_price = result.data[0]["price"]
    prev_url = result.data[0].get("product_url", "")

    # Only compare if same product URL (avoids dedup collision false positives)
    if product_url and prev_url and product_url != prev_url:
        return None

    if prev_price <= 0 or current_price <= 0:
        return None

    drop_pct = (prev_price - current_price) / prev_price
    if 0.10 <= drop_pct <= 0.50:
        return prev_price
    return None


def refine_category_for_product(name: str, default: Optional[str]) -> Optional[str]:
    """Override the supplier-derived category based on product name keywords.

    Most products are categorized via CATEGORY_MAP (supplier_category → our slug).
    This hook handles the rare case where products from one source category
    should be split into a more specific destination — currently used only
    for suero fisiológico, which has its own category but arrives lumped
    under broader supplier types like "Insumos Médicos".

    Add new rules sparingly. Per-product overrides scale poorly; prefer
    extending CATEGORY_MAP when possible.
    """
    if not name:
        return default
    # Suero fisiológico — irrigation saline (NaCl 0.9%). Has its own category
    # because no existing dental taxonomy covers it. Match Chilean naming variants:
    # "Suero Fisiológico", "Suero Salino", "Solución Salina Fisiológica",
    # "Cloruro de Sodio 0.9% / 0,9% / al 0.9% / al 0,9%", "NaCl 0.9% / 0,9%".
    # Pattern kept in sync with the DB-side backfill regex in migration
    # backfill_suero_fisiologico_categorization (2026-05-08).
    if _SALINE_PATTERN.search(_strip_accents(name)):
        return 'suero-fisiologico'
    return default


def main():
    global _product_cache

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        logger.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    supabase = create_client(url, key)

    # Preload product cache for fuzzy matching
    _product_cache = ProductCache()
    _product_cache.load(supabase)

    total_prices = 0
    total_products_created = 0
    total_errors = 0
    total_skipped = 0

    for scraper in SCRAPERS:
        logger.info(f"=== Starting scraper: {scraper.name} ===")

        # Ensure supplier exists
        supplier_id = ensure_supplier(supabase, scraper)
        if not supplier_id:
            total_errors += 1
            continue

        # Test scraper connectivity
        try:
            if not scraper.test():
                logger.warning(f"[{scraper.name}] Connection test FAILED - skipping")
                total_skipped += 1
                try:
                    scraper.close()
                except Exception:
                    pass
                continue
        except Exception as e:
            logger.error(f"[{scraper.name}] Connection test crashed: {e} - skipping")
            total_skipped += 1
            try:
                scraper.close()
            except Exception:
                pass
            continue

        try:
            products = scraper.scrape()
            logger.info(f"[{scraper.name}] Scraped {len(products)} products")

            for product in products:
                # Map the supplier's category to our category
                supplier_category = product.get("_category", "")
                our_category = CATEGORY_MAP.get(supplier_category)
                # Per-product refinement (e.g. suero fisiológico from "Insumos Médicos")
                our_category = refine_category_for_product(product["name"], our_category)

                # Get or create product (with image and brand if available)
                product_id = ensure_product(
                    supabase,
                    product["name"],
                    our_category,
                    image_url=product.get("image_url"),
                    brand=product.get("brand"),
                )
                if not product_id:
                    logger.warning(f"[{scraper.name}] Could not create product: {product['name']}")
                    continue

                # Check for restock event before inserting new price
                check_and_record_restock(
                    supabase, product_id, supplier_id,
                    product.get("in_stock", True),
                )

                # Use explicit sale price if scraper found one; otherwise check for price drop
                original_price = product.get("original_price")
                if original_price is None:
                    try:
                        original_price = detect_price_drop(
                            supabase, product_id, supplier_id, product["price"],
                            product_url=product.get("product_url", "")
                        )
                    except Exception as e:
                        logger.warning(f"[{scraper.name}] detect_price_drop failed: {e}")
                        original_price = None
                if original_price:
                    product["original_price"] = original_price

                # Insert price record
                try:
                    retry_supabase(lambda: supabase.table("prices").insert({
                        "product_id": product_id,
                        "supplier_id": supplier_id,
                        "price": product["price"],
                        "product_url": product.get("product_url", ""),
                        "in_stock": product.get("in_stock", True),
                        "original_price": product.get("original_price"),  # None if no sale
                    }).execute())
                    total_prices += 1
                except Exception as e:
                    logger.warning(f"[{scraper.name}] Price insert failed: {e}")

        except Exception as e:
            logger.error(f"[{scraper.name}] Scraper failed: {e}")
            total_errors += 1
        finally:
            # Release Playwright/browser resources if this scraper used them
            try:
                scraper.close()
            except Exception as _close_err:
                logger.warning(f"[{scraper.name}] close() raised: {_close_err}")

    logger.info(f"=== DONE ===")
    logger.info(f"  Prices inserted: {total_prices}")
    logger.info(f"  Skipped (blocked): {total_skipped}")
    logger.info(f"  Errors: {total_errors}")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            from base_scraper import shutdown_shared_browser
            shutdown_shared_browser()
        except Exception:
            pass
