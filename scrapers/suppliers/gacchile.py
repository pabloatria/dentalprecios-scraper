"""
Scraper for GAC Chile (gacchile.cl)
Platform: WooCommerce
Products: Orthodontic supplies — brackets, arcos, alambres, bandas, instrumentos
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List
from suppliers.woo_generic import WooGenericScraper


class GacChileScraper(WooGenericScraper):
    name = "GAC Chile"
    base_url = "https://gacchile.cl"
    website_url = "https://gacchile.cl"

    categories = [
        "ali",
        "adhesivos",
        "anclaje",
        "arcos-y-alambres",
        "auxiliares",
        "bandas",
        "brackets",
        "consulta-y-laboratorio",
        "elastomericos",
        "instrumentos",
        "ortopedia-dental",
        "tubos",
    ]

    category_url_pattern = "/categoria-producto/{category}/"
    product_selector = "div.item-col"
    link_selector = "a.woocommerce-LoopProduct-link"
