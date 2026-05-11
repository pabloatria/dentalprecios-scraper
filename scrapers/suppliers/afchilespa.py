"""
Scraper for AF Chile SPA (afchilespa.cl)
Platform: WooCommerce + Woodmart theme
Products: Medical/dental supplies, syringes, disposables
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List, Dict
from suppliers.woo_generic import WooGenericScraper


class AfchilespaScraper(WooGenericScraper):
    name = "AF Chile SPA"
    base_url = "https://afchilespa.cl"
    website_url = "https://afchilespa.cl"
    use_playwright_stealth = True

    # Flat shop pagination
    categories = []
    shop_url = "/tienda/"
    pagination_style = "query"
    # Woodmart theme uses div.product instead of li.product
    product_selector = "div.product, li.product"
    # Woodmart uses different link structure
    link_selector = "a.product-image-link, a.woocommerce-LoopProduct-link"
    title_selectors = [
        ".wd-entities-title a",
        "h3.product-title a",
        "h2.woocommerce-loop-product__title",
        "h3.woocommerce-loop-product__title",
        ".product-element-top a.product-image-link",
        "h2", "h3",
    ]
