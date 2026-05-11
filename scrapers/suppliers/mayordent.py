"""
Scraper for Mayordent (mayordent.cl)
Platform: WooCommerce — uses WC Store API
Cloudflare protected — uses cloudscraper
Products: Large catalog (insumos, instrumental, equipamiento, etc.)
Prices: CLP, publicly visible via Store API
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MayordentScraper(BaseScraper):
    name = "Mayordent"
    base_url = "https://www.mayordent.cl"
    website_url = "https://www.mayordent.cl"
    use_cloudscraper = True
    use_playwright_stealth = True

    api_url = "https://www.mayordent.cl/wp-json/wc/store/v1/products"
    page_size = 100

    def scrape(self) -> List[Dict]:
        """Scrape all products via WC Store API."""
        all_products = []
        page = 1

        while page <= 100:  # Mayordent has a huge catalog
            try:
                import time, random
                time.sleep(random.uniform(1, 2))
                response = self.session.get(
                    self.api_url,
                    params={"per_page": self.page_size, "page": page},
                    timeout=30,
                )
                if response.status_code != 200:
                    break

                data = response.json()
                if not isinstance(data, list) or not data:
                    break

                for product in data:
                    try:
                        item = self._parse_product(product)
                        if item:
                            all_products.append(item)
                    except Exception as e:
                        logger.warning(f"[{self.name}] Error parsing: {e}")
                        continue

                print(f"  [{self.name}] Page {page}: {len(data)} products (total: {len(all_products)})")

                if len(data) < self.page_size:
                    break

                page += 1

            except Exception as e:
                logger.error(f"[{self.name}] API error page {page}: {e}")
                break

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, product: dict) -> Optional[Dict]:
        """Parse a WC Store API product."""
        name = product.get("name", "").strip()
        if not name:
            return None

        prices = product.get("prices", {})
        sale_price_str = prices.get("sale_price", "")
        regular_price_str = prices.get("price", "0")

        price_str = sale_price_str if sale_price_str else regular_price_str
        try:
            price = int(price_str)
        except (ValueError, TypeError):
            return None

        # Detect active promotion: sale_price is set AND lower than regular price
        original_price = None
        try:
            if sale_price_str:
                regular = int(regular_price_str)
                if regular > price:
                    original_price = regular
        except (ValueError, TypeError):
            pass

        if price <= 0:
            return None

        permalink = product.get("permalink", "")
        in_stock = product.get("is_purchasable", True)

        categories = product.get("categories", [])
        category = categories[0]["slug"] if categories else ""

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
        if original_price:
            result["original_price"] = original_price

        return result

    def test(self) -> bool:
        """Test the Store API."""
        try:
            response = self.session.get(
                self.api_url,
                params={"per_page": 5, "page": 1},
                timeout=15,
            )
            if response.status_code != 200:
                print(f"ERROR: {self.name} API returned {response.status_code}")
                return False

            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            print(f"OK: Found {count} products via API on {self.name}")
            return count > 0
        except Exception as e:
            print(f"ERROR: {self.name} API failed: {e}")
            return False
