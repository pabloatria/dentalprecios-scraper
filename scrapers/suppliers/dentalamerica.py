"""
Scraper for Dental America (dentalamerica.cl)
Platform: WooCommerce + Elementor
Products: Dental equipment, sillones dentales
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List, Dict
from suppliers.woo_generic import WooGenericScraper


class DentalamericaScraper(WooGenericScraper):
    name = "Dental America"
    base_url = "https://dentalamerica.cl"
    website_url = "https://dentalamerica.cl"
    use_playwright_stealth = True

    # Flat shop pagination
    categories = []
    shop_url = "/tienda/"
    pagination_style = "path"
    product_selector = "li.product"
