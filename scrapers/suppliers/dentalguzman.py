"""
Scraper for Dental Guzman (dentalguzman.cl)
Platform: WooCommerce (Store API disabled, HTML scraping)
Products: ~159 dental supplies
Prices: CLP, publicly visible
Note: Site uses plain (non-pretty) permalinks, so shop URL is /?post_type=product
"""
from __future__ import annotations

from typing import List, Dict
from suppliers.woo_generic import WooGenericScraper


class DentalGuzmanScraper(WooGenericScraper):
    name = "Dental Guzman"
    base_url = "https://dentalguzman.cl"
    website_url = "https://dentalguzman.cl"

    # Plain permalinks: shop page is /?post_type=product, pagination via &paged=N
    categories = []
    shop_url = "/?post_type=product"
    pagination_style = "query"
    product_selector = "li.product"
