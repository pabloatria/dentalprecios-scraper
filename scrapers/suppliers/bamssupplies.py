"""
Scraper for BAMS Supplies (bamssupplies.com)
Platform: Shopify — uses public /products.json API
Products: Facial aesthetic supplies (fillers, biostimulators, threads, toxins)
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class BamsSuppliesScraper(ShopifyGenericScraper):
    name = "BAMS Supplies"
    base_url = "https://www.bamssupplies.com"
    website_url = "https://www.bamssupplies.com"
