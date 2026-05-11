"""
Scraper for Clandent (clandent.cl)
Platform: WooCommerce + Elementor
Products: Dental instruments, supplies
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List, Dict
from suppliers.woo_generic import WooGenericScraper


class ClandentScraper(WooGenericScraper):
    name = "Clandent"
    base_url = "https://clandent.cl"
    website_url = "https://clandent.cl"

    # No categories - use flat shop pagination
    categories = []
    shop_url = "/tienda/"
    pagination_style = "path"
    product_selector = "li.product"
