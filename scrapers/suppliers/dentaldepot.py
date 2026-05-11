"""
Scraper for Dental Depot (dentaldepot.cl)
Platform: Shopify
Products: Dental consumables, instruments, equipment, orthodontics
Prices: CLP, publicly visible
Notable: compare_at_price used for original/list prices
"""
from __future__ import annotations

from typing import Optional, Dict
from suppliers.shopify_generic import ShopifyGenericScraper
from matchers import extract_brand


class DentalDepotScraper(ShopifyGenericScraper):
    name = "Dental Depot"
    base_url = "https://www.dentaldepot.cl"
    website_url = "https://www.dentaldepot.cl"
    vendor_is_brand = False  # Vendor is the store name, not product brand

    def __init__(self):
        super().__init__()
        # Shopify returns brotli by default; requests can't decode it
        self.session.headers["Accept-Encoding"] = "gzip, deflate"

    def _parse_product(self, product: dict) -> Optional[Dict]:
        """Parse product with original_price from compare_at_price."""
        result = super()._parse_product(product)
        if not result:
            return None

        # Extract compare_at_price (original/list price before discount)
        variants = product.get("variants", [])
        original_price = 0
        for variant in variants:
            cap = self._parse_price(variant.get("compare_at_price", "0"))
            if cap > 0 and (original_price == 0 or cap < original_price):
                original_price = cap

        if original_price and original_price > result["price"]:
            result["original_price"] = original_price

        return result
