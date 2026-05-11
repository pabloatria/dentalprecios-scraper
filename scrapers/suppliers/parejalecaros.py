"""
Scraper for Pareja Lecaros (parejalecaros.cl)
Platform: Shopify
Products: Composites, endodontics, impressions, lab materials, instruments
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class ParejaLecarosScraper(ShopifyGenericScraper):
    name = "Pareja Lecaros"
    base_url = "https://parejalecaros.cl"
    website_url = "https://parejalecaros.cl"
    vendor_is_brand = False  # Shopify vendor is the store name, not the product brand
