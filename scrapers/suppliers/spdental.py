"""
Scraper for SP Dental (spdental.shop)
Platform: Shopify
Products: Resins, adhesives, implantology, whitening, orthodontics (FGM brand)
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class SpDentalScraper(ShopifyGenericScraper):
    name = "SP Dental"
    base_url = "https://spdental.shop"
    website_url = "https://spdental.shop"
    use_playwright_stealth = True
