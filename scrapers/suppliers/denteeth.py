"""
Scraper for Denteeth (denteeth.cl)
Platform: WooCommerce + Woodmart theme
Products: Dental instruments, lab supplies, orthodontics, endodontics
Prices: CLP, publicly visible

Note: Main categories (endodoncia, fresas, laboratorio-2, ortodoncia, restauracion)
show subcategory grids instead of products. We scrape subcategory pages directly.
Categories cirugia, descartables, periodoncia, rotatorio show products directly.
"""
from __future__ import annotations

from typing import Optional, List, Dict
from suppliers.woo_generic import WooGenericScraper


class DenteethScraper(WooGenericScraper):
    name = "Denteeth"
    base_url = "https://denteeth.cl"
    website_url = "https://denteeth.cl"

    category_url_pattern = "/categoria-producto/{category}/"

    categories = [
        # Direct product categories
        "cirugia",
        "descartables",
        "periodoncia",
        "rotatorio",
        # Endodoncia subcategories
        "endodoncia/accesorios",
        "endodoncia/equipamiento-y-profilaxis",
        "endodoncia/instrumentacion",
        "endodoncia/medicacion",
        "endodoncia/obturacion",
        # Fresas subcategories
        "fresas/carbide",
        "fresas/diamante",
        "fresas/kits",
        "fresas/laboratorio",
        # Laboratorio subcategories
        "laboratorio-2/accesorios-laboratorio-2",
        "laboratorio-2/ceramicas-sobre-metal",
        "laboratorio-2/ceras",
        "laboratorio-2/ceromeros",
        "laboratorio-2/equipamiento",
        "laboratorio-2/fresado-e-inyeccion",
        "laboratorio-2/impresion-3d",
        "laboratorio-2/organizacion-y-packing",
        "laboratorio-2/pinceles-y-talladores",
        "laboratorio-2/siliconasyyeso",
        "laboratorio-2/stains",
        "laboratorio-2/termoformado",
        # Ortodoncia subcategories
        "ortodoncia/accesorios-ortodoncia",
        "ortodoncia/anclaje",
        "ortodoncia/arcos",
        "ortodoncia/bandas-y-tubos",
        "ortodoncia/brackets",
        "ortodoncia/cementos",
        "ortodoncia/elastomeros",
        "ortodoncia/instrumental-ortodoncia",
        "ortodoncia/ortopedia-ortodoncia",
        # Restauracion subcategories
        "restauracion/blanqueamiento",
        "restauracion/resinas-y-cementos",
        "restauracion/fotocurado",
        "restauracion/fotografia",
        "restauracion/grabado-y-adhesion",
        "restauracion/impresion",
        "restauracion/instrumental-restauracion",
        "restauracion/matrices",
        "restauracion/odontopediatria",
        "restauracion/postes",
        "restauracion/prevencion",
        "restauracion/recursos-abrasivos",
    ]

    pagination_style = "path"

    # Woodmart theme uses div.product-grid-item instead of li.product
    product_selector = "div.product-grid-item"
    title_selectors = [
        "h3.wd-entities-title",
        "h2.wd-entities-title",
    ]
    link_selector = "a.product-image-link"

    def _parse_product(self, el, category: str = "") -> Optional[Dict]:
        """Override to map subcategory paths to parent category."""
        result = super()._parse_product(el, category)
        if result and result.get("_category"):
            # Strip subcategory: "endodoncia/accesorios" → "endodoncia"
            result["_category"] = result["_category"].split("/")[0]
        return result
