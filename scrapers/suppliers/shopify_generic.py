"""
Generic Shopify scraper using the public products.json API.
Much more reliable than HTML scraping for Shopify stores.
"""
from __future__ import annotations

import re
import json
import logging
from typing import Optional, List, Dict
from base_scraper import BaseScraper
from matchers import extract_brand

logger = logging.getLogger(__name__)


class ShopifyGenericScraper(BaseScraper):
    """Generic Shopify scraper using /products.json API."""

    name = "ShopifyGeneric"
    base_url = ""
    website_url = ""

    # Set to False when the Shopify vendor field is the store name, not the product brand.
    # When False, extract_brand() from matchers will be used to detect brand from product name.
    vendor_is_brand = True

    # Number of products per API page (max 250)
    page_size = 250

    def scrape(self) -> List[Dict]:
        """Scrape all products from Shopify store via JSON API."""
        all_products = []
        page = 1

        while True:
            url = f"{self.base_url}/products.json?limit={self.page_size}&page={page}"

            try:
                import time
                import random
                time.sleep(random.uniform(1, 3))

                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.error(f"[{self.name}] Error fetching page {page}: {e}")
                break

            products = data.get("products", [])
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
        """Parse a Shopify product JSON object."""
        title = product.get("title", "").strip()
        if not title:
            return None

        handle = product.get("handle", "")
        product_url = f"{self.base_url}/products/{handle}" if handle else ""

        # Get the first available variant price
        variants = product.get("variants", [])
        if not variants:
            return None

        price = 0
        in_stock = False

        for variant in variants:
            variant_price = self._parse_price(variant.get("price", "0"))
            if variant_price > 0:
                if price == 0 or variant_price < price:
                    price = variant_price
                if variant.get("available", False):
                    in_stock = True

        if price <= 0:
            return None

        # Get vendor/brand
        vendor = product.get("vendor", "")
        product_type = product.get("product_type", "")

        # Determine brand: use vendor if it's a real brand, otherwise extract from name
        brand = None
        if vendor and self.vendor_is_brand:
            from matchers import is_valid_brand
            brand = vendor if is_valid_brand(vendor) else extract_brand(title)
        else:
            brand = extract_brand(title)

        # Get product image
        images = product.get("images", [])
        image_url = images[0].get("src", "") if images else ""

        result = {
            "name": title,
            "price": price,
            "product_url": product_url,
            "in_stock": in_stock,
        }

        if brand:
            result["brand"] = brand
        if product_type:
            # Normalize whitespace: some Shopify stores embed NBSP (\xa0) in
            # product_type strings (e.g. geerdink's "Insumos\xa0Desechables").
            # Lowercase + collapse whitespace so CATEGORY_MAP keys stay clean.
            normalized = re.sub(r'\s+', ' ', product_type.replace('\xa0', ' ')).strip().lower()
            if normalized:
                result["_category"] = normalized
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_price(self, price_str: str) -> int:
        """Parse Shopify price string to CLP integer.
        Shopify prices are in cents for most currencies, but for CLP
        they may be whole numbers. Check both cases."""
        if not price_str:
            return 0
        try:
            # Remove any non-numeric except dots
            cleaned = re.sub(r'[^\d.]', '', str(price_str))
            price_float = float(cleaned)
            # Shopify CLP prices are typically whole numbers (no decimals)
            return int(price_float)
        except (ValueError, TypeError):
            return 0

    def test(self) -> bool:
        """Test the scraper can fetch products."""
        try:
            url = f"{self.base_url}/products.json?limit=2"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            products = data.get("products", [])
            print(f"OK: Found {len(products)} products via JSON API on {self.name}")
            return len(products) > 0
        except Exception as e:
            print(f"ERROR: Could not fetch {self.name}: {e}")
            return False
