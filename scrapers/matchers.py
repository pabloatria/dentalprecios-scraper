"""
Product name normalization and similarity matching utilities.
Used by deduplicate.py and main.py for product deduplication.
"""
from __future__ import annotations

import re
import html
import unicodedata


def _strip_accents(text: str) -> str:
    """Remove accent marks: flúor -> fluor, etc."""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(name: str) -> str:
    """Normalize product name for deduplication matching."""
    name = html.unescape(name)
    name = name.lower().strip()
    # Remove TM/registered symbols
    name = re.sub(r'[™®©]', '', name)
    # Remove leftover HTML entities
    name = re.sub(r'&#\d+;', ' ', name)
    # Remove HTML <br> tags
    name = re.sub(r'<br\s*/?>', ' ', name)
    # Strip accents (flúor -> fluor)
    name = _strip_accents(name)
    # Join decimal numbers before removing punctuation: "2.1" → "21"
    name = re.sub(r'(\d+)\.(\d+)', r'\1\2', name)
    # Remove all punctuation except alphanumeric and spaces
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name)
    # Remove number+unit patterns: "10gr" → "10", "25mm" → "25", "100ml" → "100"
    # Unit must be directly adjacent (no space) to preserve standalone L, R, G, etc.
    name = re.sub(r'\b(\d+)(gr|grs|g|ml|mm|cc|oz|kg|mg|cm|lt|l)\b', r'\1', name)
    # Remove quantity-only suffixes (keep concentration/size numbers)
    name = re.sub(
        r'\b(und|unid|unidad|unidades|unidosis|pza|pieza|piezas|uds|ud|dosis|'
        r'unit|dose|doses|units)\b',
        '', name
    )
    # Normalize "x 100" / "x100" quantity patterns
    name = re.sub(r'\bx\s*(\d+)\b', r'\1', name)
    # Normalize common Spanish/English dental term translations
    translations = {
        'jeringa': 'syringe', 'jeringas': 'syringe',
        'tubo': 'tube', 'tubos': 'tube',
        'capsula': 'capsule', 'capsulas': 'capsule', 'capsules': 'capsule',
        'tratamiento': 'treatment',
        'blanqueamiento': 'whitening',
        'resina': 'resin', 'resinas': 'resin',
        'adhesivo': 'adhesive',
        'cemento': 'cement',
        'fluoruro': 'fluoride', 'fluor': 'fluoride',
    }
    for es, en in translations.items():
        name = re.sub(rf'\b{es}\b', en, name)
    # Remove common filler words (Spanish + English)
    name = re.sub(
        r'\b(de|del|con|para|en|por|y|the|and|for|with|of|a|la|el|las|los|un|una)\b',
        '', name
    )
    # Remove dental descriptor noise (words that describe but don't identify)
    # NOTE: "kit" is intentionally kept — it differentiates kits from single units
    name = re.sub(
        r'\b(treatment|fluoride|sodio|sodium|barniz|sabor|flavor|'
        r'recubrimiento|protector|protective|coating|intro|acc|accesorios)\b',
        '', name
    )
    # Remove flavor names (variants, not different products for pricing)
    name = re.sub(
        r'\b(menta|mint|melon|sandia|watermelon|fresa|strawberry|tutti|'
        r'frutti|chicle|bubblegum|bubble|gum)\b',
        '', name
    )
    # Remove manufacturer company names (noise alongside product sub-brands)
    name = re.sub(
        r'\b(3m|espe|solventum|dentsply|sirona|vivadent)\b',
        '', name
    )
    # Normalize CAD/CAM block product names so different suppliers match:
    # "Bloques Ivoclar Empress Multi" <-> "IPS EMPRESS CAD MULTI CEREC/INLAB"
    name = re.sub(
        r'\b(cerec|inlab|programat|primemill|primescan)\b',
        '', name
    )
    name = re.sub(r'\b(bloques|bloque|blocks)\b', 'block', name)
    name = re.sub(r'\bips\b', '', name)
    name = re.sub(r'\bcad\b', '', name)
    # Collapse whitespace again
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def tokenize(name: str) -> set:
    """Get meaningful tokens from a normalized name.

    Keeps single-character tokens because they can be critical
    differentiators in dental products (e.g., Lima H vs Lima K,
    Forcep 18L vs 18R).
    """
    normalized = normalize_name(name)
    return set(normalized.split())


def extract_numbers(name: str) -> set:
    """Extract specification numbers from a normalized name.

    These are numbers that distinguish product variants:
    concentrations (35%), sizes (25mm), model numbers (#20), etc.
    """
    normalized = normalize_name(name)
    return set(re.findall(r'\d+', normalized))


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two token sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def containment_similarity(set_a: set, set_b: set) -> float:
    """How much of the smaller set is contained in the larger set."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    return len(intersection) / min(len(set_a), len(set_b))


def pick_canonical_name(names: list) -> str:
    """Pick the best canonical name from the group.

    Prefers names that:
    1. Contain a known brand
    2. Are shorter (more concise)
    """
    if not names:
        return ""
    if len(names) == 1:
        return names[0]

    # Prefer names with a known brand, then shortest
    with_brand = [n for n in names if extract_brand(n) is not None]
    candidates = with_brand if with_brand else names
    return sorted(candidates, key=len)[0]


KNOWN_BRANDS = [
    "3m", "solventum", "dentsply", "ivoclar", "kerr", "gc", "voco",
    "coltene", "ultradent", "maquira", "fgm", "angelus", "kulzer",
    "zhermack", "bisco", "septodont", "hu-friedy", "nsk", "woodpecker",
    "medit", "phrozen", "asiga", "scheu", "nextdent", "formlabs",
    "orbis", "peclab", "wanhao", "espe", "clinpro", "tokuyama",
    "shofu", "premier", "sdi", "densco", "bredent", "vita",
    "straumann", "nobel biocare", "osstem", "neodent", "megagen",
    "galderma", "merz", "allergan",
    "biodinamica", "eighteeth", "renfert", "kuraray", "dte",
    "coltene", "sprintray", "detax", "mani", "microdont",
]

# Supplier names that should NEVER be used as brands
SUPPLIER_NAMES = {
    "parejalecaroschile", "parejalecarosch", "pareja lecaros",
    "eksadental", "eksa dental", "orbisdental", "orbis dental",
    "clandent", "mayordent", "mayor dent", "biotech chile",
    "depodental", "dentalmarket", "dental market", "surdent",
    "expressdent", "dental store", "3dental", "tres dental",
    "dentobal", "techdent", "tech dent", "dentamarket",
    "dental macaya", "tienda dentinet", "dentinet",
    "cadcam service", "dentaltech", "dental america",
}


def is_valid_brand(brand: str) -> bool:
    """Check if a string is a valid brand (not a supplier name)."""
    return brand.lower().strip() not in SUPPLIER_NAMES


def extract_brands(name: str) -> set[str]:
    """Extract ALL matching brands from a product name."""
    name_lower = name.lower()
    found = set()
    for brand in KNOWN_BRANDS:
        if brand in name_lower:
            found.add(brand.upper())
    return found


def extract_brand(name: str) -> str | None:
    """Try to extract the primary brand from product name."""
    brands = extract_brands(name)
    if not brands:
        return None
    # Return the longest match (more specific: "NOBEL BIOCARE" over "GC")
    return max(brands, key=len)


def shared_brand(name_a: str, name_b: str) -> bool:
    """Check if two product names share any known brand."""
    brands_a = extract_brands(name_a)
    brands_b = extract_brands(name_b)
    return bool(brands_a & brands_b)


def _has_packaging_keyword(name: str) -> bool:
    """Check if a product name contains a packaging/quantity keyword."""
    lowered = normalize_name(name)
    return bool(re.search(r'\b(kit|set|pack|combo|surtido|estuche|sistema|system)\b', lowered))


# Unit containers that define a pack's countable unit.
# When a number appears adjacent to one of these, it's the pack size.
_PACK_UNIT_PATTERN = (
    r'jeringas?|syringes?|'
    r'tubos?|tubes?|'
    r'capsulas?|capsules?|caps?|'
    r'ampolla(?:s)?|ampoule(?:s)?|'
    r'viales?|vials?|'
    r'frasco(?:s)?|bottle(?:s)?|'
    r'unidades?|units?|'
    r'cartuchos?|cartridges?|carpulas?|'
    r'sachets?|'
    r'envases?|'
    r'paquetes?|packages?|'
    r'guantes?|gloves?|'
    r'agujas?|needles?|'
    r'gasas?|gauze|'
    r'mascarillas?|masks?|'
    r'pares?|'
    r'cajas?|boxes?|'
    r'bolsas?|bags?'
)

# Tokens that indicate the preceding number is a model/catalog code, not a pack count.
# Tested against the substring immediately before a candidate digit match.
_MODEL_CODE_PREFIX = re.compile(
    r'\b(?:modelo|ref|referencia|codigo|cod|cat|catalog|catalogo)\.?\s*$'
)


def extract_pack_count(name: str) -> int | None:
    """Extract an explicit pack count from a product name.

    Looks for patterns where an integer is adjacent to a countable unit
    (jeringa, tubo, ampolla, vial, frasco, cápsula, unidad, cartucho…).
    Returns None when no reliable pack count is found — do NOT guess.

    Examples that return 2:
      "2 Jeringas Restaurador Fluido Filtek Z350 Flow"
      "Filtek Z350 XT Flow Tono A1 (2 Jeringas)"
      "Pack de 2 tubos de ionómero"
      "Cementos x 3 cápsulas"
      "Composite Z250 – 3 jeringas"

    Examples that return None (ambiguous / no unit):
      "Filtek Z350 XT Flow"                 — no count/unit
      "Filtek Bulk Fill Flow"                — no count/unit
      "Lima Hedström 25mm"                   — size, not pack
      "Ionómero al 30%"                      — concentration, not pack
      "Pack económico"                       — word but no number
    """
    if not name:
        return None

    # Work on a light pre-normalization: lowercase, strip accents, collapse ws.
    n = _strip_accents(html.unescape(name).lower())
    n = re.sub(r'[™®©]', '', n)
    # Convert punctuation that can abut numbers/units to spaces while keeping
    # digits + letters + spaces intact.
    n = re.sub(r'[^a-z0-9\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()

    patterns = [
        # "2 jeringas", "3 tubos", "1 vial"
        rf'\b(\d{{1,3}})\s+(?:{_PACK_UNIT_PATTERN})\b',
        # "jeringas x 2", "tubos x 3"
        rf'\b(?:{_PACK_UNIT_PATTERN})\s*x\s*(\d{{1,3}})\b',
        # "x 2 jeringas", "x2 jeringas" (x-prefixed quantity)
        rf'\bx\s*(\d{{1,3}})\s+(?:{_PACK_UNIT_PATTERN})\b',
        # "pack de 2 jeringas", "caja de 3 tubos", "set de 4 capsulas"
        rf'\b(?:pack|caja|set|estuche)\s+de?\s+(\d{{1,3}})\s+(?:{_PACK_UNIT_PATTERN})\b',
        # Bare "Pack 200", "Paquete 50" — no de, no inner unit.
        # Restricted to "pack/paquete" because "caja N" is too generic.
        r'\b(?:pack|paquete)\s+(\d{1,3})\b',
    ]
    for pat in patterns:
        m = re.search(pat, n)
        if m:
            try:
                count = int(m.group(1))
            except (IndexError, ValueError):
                continue
            # Reject if a model/catalog-code keyword sits immediately before the digit.
            # Catches "Modelo 500 jeringas ref", "Cod. 100 agujas", etc.
            preceding = n[: m.start(1)].rstrip()
            if _MODEL_CODE_PREFIX.search(preceding):
                continue
            # Sanity bound. Medical commodities ship in cajas x200, x500;
            # numbers above 500 are almost always catalog codes.
            if 1 <= count <= 500:
                return count

    # Fallback: loose "x N" anywhere in the name, only if the name contains
    # a known pack-unit noun somewhere. Catches "Agujas Hipodérmicas 21G x 100"
    # where the unit (agujas) is separated from the count by other tokens.
    if re.search(rf'\b(?:{_PACK_UNIT_PATTERN})\b', n):
        m = re.search(r'\bx\s*(\d{1,3})\b', n)
        if m:
            try:
                count = int(m.group(1))
            except (IndexError, ValueError):
                return None
            preceding = n[: m.start(1)].rstrip()
            if not _MODEL_CODE_PREFIX.search(preceding) and 1 <= count <= 500:
                return count
    return None


def are_same_product(name_a: str, name_b: str, threshold: float = 0.70) -> bool:
    """Determine if two product names refer to the same product.

    Conservative matching that requires:
    1. High Jaccard similarity (default 0.70)
    2. Compatible specification numbers (sizes, concentrations, etc.)
    3. Compatible packaging (kit vs single unit = different product)

    Number compatibility: if both have numbers, one set must be a subset
    of the other (or equal). This allows "Product 100" to match
    "Product 2.1% 100" while still blocking "Product 35%" vs "Product 16%".
    """
    tokens_a = tokenize(name_a)
    tokens_b = tokenize(name_b)

    if not tokens_a or not tokens_b:
        return False

    # Packaging mismatch: if one is a kit/set and the other isn't, they're different
    pkg_a = _has_packaging_keyword(name_a)
    pkg_b = _has_packaging_keyword(name_b)
    if pkg_a != pkg_b:
        return False

    # Pack-size mismatch: "2 jeringas" is NOT the same SKU as "1 jeringa".
    # Only fires when both names have an extractable pack count — avoids
    # false-splitting names that simply omit pack info.
    pack_a = extract_pack_count(name_a)
    pack_b = extract_pack_count(name_b)
    if pack_a is not None and pack_b is not None and pack_a != pack_b:
        return False

    # Extract specification numbers
    nums_a = extract_numbers(name_a)
    nums_b = extract_numbers(name_b)

    # Number compatibility: if both have numbers, one must be a subset of the other
    if nums_a and nums_b:
        if not (nums_a <= nums_b or nums_b <= nums_a):
            return False

    # Differentiator check: if the only difference between the two names is
    # a purely alphabetic word (like DENTIN vs OPAQUE vs ENAMEL), they are
    # different products in the same product line, not duplicates.
    diff_a = tokens_a - tokens_b
    diff_b = tokens_b - tokens_a
    # Only consider purely alphabetic tokens as meaningful differentiators
    alpha_a = {t for t in diff_a if t.isalpha()}
    alpha_b = {t for t in diff_b if t.isalpha()}
    if alpha_a and alpha_b and len(alpha_a) <= 2 and len(alpha_b) <= 2:
        # Both sides have a unique distinguishing word — different products
        return False

    sim = jaccard_similarity(tokens_a, tokens_b)
    return sim >= threshold
