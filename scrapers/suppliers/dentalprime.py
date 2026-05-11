"""
Scraper for Dental Prime (tienda.dentalprime.cl)
Platform: WooCommerce (Themestarter theme - uses <section> not <li> for products)
Products: Adhesivos tisulares, suturas dentales
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List
from suppliers.woo_generic import WooGenericScraper


class DentalPrimeScraper(WooGenericScraper):
    name = "Dental Prime"
    base_url = "https://tienda.dentalprime.cl"
    website_url = "https://tienda.dentalprime.cl"

    categories = [
        "adhesivos",
        "suturas",
    ]

    category_url_pattern = "/categoria-producto/{category}/"

    # This theme uses <section class="product"> instead of <li class="product">
    product_selector = "section.product"
    title_selectors = [
        "h3.product-name",
        "h2.product-name",
        "h3.heading-title",
        "h3",
    ]
    # Links don't have woocommerce class, use thumbnail wrapper link
    link_selector = ".thumbnail-wrapper > a"
