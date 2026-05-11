"""
Scraper for Depo Dental (depodental.cl)
Platform: WooCommerce (Store API)
Cloudflare protected — uses cloudscraper
Products: Composites, endodontics, instruments, orthodontics, whitening, etc.
Prices: CLP, publicly visible
"""
from __future__ import annotations

import re
import time
import random
import logging
from typing import Optional, List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class DepodentalScraper(BaseScraper):
    name = "Depo Dental"
    base_url = "https://depodental.cl"
    website_url = "https://depodental.cl"
    use_cloudscraper = True

    # WooCommerce Store API endpoint (public, no auth needed)
    api_url = "https://depodental.cl/wp-json/wc/store/v1/products"
    page_size = 50

    def scrape(self) -> List[Dict]:
        """Scrape all products via WooCommerce Store API."""
        all_products = []
        page = 1

        while True:
            url = f"{self.api_url}?per_page={self.page_size}&page={page}"

            try:
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
        """Parse a WooCommerce Store API product object."""
        name = product.get("name", "").strip()
        if not name:
            return None

        permalink = product.get("permalink", "")

        # Price from prices object (in minor units or string)
        prices = product.get("prices", {})
        price = 0
        sale_price = prices.get("sale_price", "0")
        regular_price = prices.get("price", "0")

        # WooCommerce Store API returns prices as strings in minor units
        try:
            price = int(sale_price) if sale_price and int(sale_price) > 0 else int(regular_price)
        except (ValueError, TypeError):
            pass

        # Adjust for decimal places (CLP has 0 decimals typically)
        decimal_count = prices.get("currency_minor_unit", 0)
        if decimal_count and decimal_count > 0:
            price = price // (10 ** decimal_count)

        if price <= 0:
            return None

        # Stock status
        in_stock = product.get("is_purchasable", False) and product.get("stock_status", "") == "instock"

        # Image
        image_url = ""
        images = product.get("images", [])
        if images:
            image_url = images[0].get("src", "")

        # Brand from attributes or tags
        brand = ""
        for attr in product.get("attributes", []):
            if attr.get("name", "").lower() in ("marca", "brand"):
                terms = attr.get("terms", [])
                if terms:
                    brand = terms[0].get("name", "")
                break

        result = {
            "name": name,
            "price": price,
            "product_url": permalink,
            "in_stock": in_stock,
        }
        if brand:
            result["brand"] = brand
        if image_url:
            result["image_url"] = image_url

        return result

    def test(self) -> bool:
        """Test the scraper can fetch products."""
        try:
            url = f"{self.api_url}?per_page=2"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            products = response.json()
            print(f"OK: Found {len(products)} products via Store API on {self.name}")
            return len(products) > 0
        except Exception as e:
            print(f"ERROR: Could not fetch {self.name}: {e}")
            return False
