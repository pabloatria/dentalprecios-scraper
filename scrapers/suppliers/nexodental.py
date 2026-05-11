"""
Scraper for NexoDental (nexodental.cl)
Platform: WooCommerce (Cloudflare-protected)
Products: Dental supplies, instruments, lab materials
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List, Dict
from suppliers.woo_generic import WooGenericScraper


class NexoDentalScraper(WooGenericScraper):
    name = "NexoDental"
    base_url = "https://nexodental.cl"
    website_url = "https://nexodental.cl"
    use_cloudscraper = True

    category_url_pattern = "/product-category/{category}/"

    categories = [
        "anestesia",
        "blanqueamiento",
        "desechables",
        "endodoncia",
        "equipos",
        "fresas-y-pulido",
        "impresion",
        "instrumental-y-accesorios",
        "laboratorio",
        "limpieza-e-higiene-bucal",
        "operatoria",
        "ortodoncia",
        "periodoncia",
        "radiografia",
    ]

    pagination_style = "path"

    # Riode theme wraps products in li.product-wrap instead of li.product
    product_selector = "li.product-wrap"
