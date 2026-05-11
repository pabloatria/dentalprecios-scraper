"""
Scraper for Geerdink (geerdink.cl)
Platform: Shopify
Products: Medical supplies, EPP, wound care — overlap with tubotiquin
          on commodity items but with different brand mix.
Prices: CLP, publicly visible.

Added 2026-05-07 as part of the dental clinic supply expansion.
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class GeerdinkScraper(ShopifyGenericScraper):
    name = "Geerdink"
    base_url = "https://geerdink.cl"
    website_url = "https://geerdink.cl"
    vendor_is_brand = False  # vendor field is mixed (Socofar/distributor, Geerdink/private,
                             # and real brands) — safer to extract brand from product name
    # No use_playwright_stealth: Shopify /products.json returns clean JSON
    # with a normal browser UA; flip to True if production scrapes start 403'ing.
