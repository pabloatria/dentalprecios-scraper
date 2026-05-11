"""
Scraper for Gexa Chile (gexachile.cl)
Platform: Shopify (Warehouse theme)
Products: Dental equipment, orthodontics, lab supplies, digital dentistry
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class GexaChileScraper(ShopifyGenericScraper):
    name = "Gexa Chile"
    base_url = "https://gexachile.cl"
    website_url = "https://gexachile.cl"
