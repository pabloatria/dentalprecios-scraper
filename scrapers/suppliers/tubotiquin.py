"""
Scraper for Tubotiquin (tubotiquin.cl)
Platform: Shopify
Products: Medical commodities — guantes, jeringas, agujas hipodérmicas,
          suero fisiológico, gasas, mascarillas, alcohol/povidona, EPP.
Prices: CLP, publicly visible.

Added 2026-05-07 as part of the dental clinic supply expansion (medical
commodities the dental specialty distributors don't reliably carry).
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class TubotiquinScraper(ShopifyGenericScraper):
    name = "Tubotiquin"
    base_url = "https://www.tubotiquin.cl"
    website_url = "https://www.tubotiquin.cl"
    vendor_is_brand = True  # tubotiquin lists real brand names in vendor field
    # No use_playwright_stealth: Shopify /products.json returns clean JSON
    # with a normal browser UA; flip to True if production scrapes start 403'ing.
