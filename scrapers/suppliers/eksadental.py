"""
Scraper for Eksa Dental (eksadental.cl)
Platform: Shopify
Products: Turbines, micromotors, surgery equipment, sterilization
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class EksaDentalScraper(ShopifyGenericScraper):
    name = "Eksa Dental"
    base_url = "https://eksadental.cl"
    website_url = "https://eksadental.cl"
    vendor_is_brand = False  # Shopify vendor is the store name, not the product brand
    use_playwright_stealth = True
