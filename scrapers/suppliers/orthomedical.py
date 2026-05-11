"""
Scraper for Orthomedical Chile (orthomedical.cl)
Platform: WooCommerce with WC Store API (products loaded via REST)
Products: Dental polishing, orthodontics, instruments
Prices: CLP, publicly visible via API
"""
from __future__ import annotations

import re
import logging
from typing import Optional, List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class OrthomedicalScraper(BaseScraper):
    name = "Orthomedical"
    base_url = "https://orthomedical.cl"
    website_url = "https://orthomedical.cl"
    use_playwright_stealth = True

    # WC Store API endpoint
    api_url = "https://orthomedical.cl/wp-json/wc/store/v1/products"
    page_size = 100

    def scrape(self) -> List[Dict]:
        """Scrape all products from WC Store API."""
        all_products = []
        page = 1

        while True:
            url = f"{self.api_url}?per_page={self.page_size}&page={page}"

            try:
                import time
                import random
                time.sleep(random.uniform(1, 3))

                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                products = response.json()
            except Exception as e:
                logger.error(f"[{self.name}] Error fetching page {page}: {e}")
                break

            if not products:
                break

            for product in products:
                try:
                    item = self._parse_product(product)
                    if item:
                        all_products.append(item)
                except Exception as e:
                    print(f"  Error parsing product: {e}")
                    continue

            if len(products) < self.page_size:
                break

            page += 1

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, product: dict) -> Optional[Dict]:
        """Parse a WC Store API product object."""
        name = product.get("name", "").strip()
        if not name:
            return None

        permalink = product.get("permalink", "")

        # Get price from prices object
        prices = product.get("prices", {})
        price_str = prices.get("price", "0")

        try:
            price = int(price_str)
        except (ValueError, TypeError):
            price = 0

        if price <= 0:
            return None

        # Check stock
        in_stock = product.get("is_purchasable", True)

        # Get category
        categories = product.get("categories", [])
        category = ""
        if categories:
            category = categories[0].get("slug", "")

        # Get product image
        images = product.get("images", [])
        image_url = images[0].get("src", "") if images else ""

        result = {
            "name": name,
            "price": price,
            "product_url": permalink,
            "in_stock": in_stock,
        }
        if category:
            result["_category"] = category
        if image_url:
            result["image_url"] = image_url

        return result

    def test(self) -> bool:
        """Test the scraper can fetch products."""
        try:
            url = f"{self.api_url}?per_page=3"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            products = response.json()
            print(f"OK: Found {len(products)} products via WC Store API on {self.name}")
            return len(products) > 0
        except Exception as e:
            print(f"ERROR: Could not fetch {self.name}: {e}")
            return False
