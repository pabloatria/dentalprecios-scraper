"""
Scraper for Orbis Dental (orbisdental.cl)
Platform: Shopify
Products: Orthodontics, skeletal anchorage, mini-implants, disposables
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class OrbisDentalScraper(ShopifyGenericScraper):
    name = "Orbis Dental"
    base_url = "https://www.orbisdental.cl"
    website_url = "https://www.orbisdental.cl"
    vendor_is_brand = False  # Shopify vendor is the store name, not the product brand
