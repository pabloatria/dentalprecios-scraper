"""
Scraper for ExpressDent (expressdent.cl)
Platform: WooCommerce
Products: Dental instruments, consumables, equipment
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List, Dict
from suppliers.woo_generic import WooGenericScraper


class ExpressDentScraper(WooGenericScraper):
    name = "ExpressDent"
    base_url = "https://expressdent.cl"
    website_url = "https://expressdent.cl"

    category_url_pattern = "/product-category/{category}/"

    categories = [
        "cirugia",
        "desechables",
        "endodoncia",
        "equipamiento",
        "esterilizacion",
        "instrumental",
        "laboratorio",
        "odontopediatria",
        "operatoria",
        "ortodoncia",
        "periodoncia",
        "prevencion",
        "rehabilitacion-oral",
        "flujo-digital",
    ]

    pagination_style = "path"
    product_selector = "li.product"
