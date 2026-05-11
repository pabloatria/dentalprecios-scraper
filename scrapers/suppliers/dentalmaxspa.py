"""
Scraper for DentalMaxSpa (dentalmaxspa.cl)
Platform: WooCommerce + Enfold theme — uses WC Store API
Products: Bone grafts, membranes, soft tissue, surgical instruments (Geistlich, META)
Prices: CLP, publicly visible via Store API
Note: Small catalog (~16 products), single API call fetches all
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class DentalMaxSpaScraper(BaseScraper):
    name = "DentalMaxSpa"
    base_url = "https://dentalmaxspa.cl"
    website_url = "https://dentalmaxspa.cl"

    api_url = "https://dentalmaxspa.cl/wp-json/wc/store/v1/products"
    page_size = 100

    # Filter out test/placeholder products
    skip_names = {"test", "test product"}

    def scrape(self) -> List[Dict]:
        """Scrape all products via WC Store API."""
        all_products = []
        page = 1

        while page <= 5:  # Small catalog, shouldn't need more than 1 page
            try:
                import time, random
                time.sleep(random.uniform(0.5, 1.5))
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
        if not name or name.lower() in self.skip_names:
            return None

        prices = product.get("prices", {})
        # Store API returns prices in centavos (e.g., 9658000 = $96.580)
        price_str = prices.get("sale_price") or prices.get("price", "0")
        try:
            price = int(price_str) // 100  # Convert centavos to CLP
        except (ValueError, TypeError):
            return None

        if price <= 100:  # Skip placeholder prices like $1, $42
            return None

        permalink = product.get("permalink", "")
        in_stock = product.get("is_purchasable", True)

        categories = product.get("categories", [])
        # Use the most specific (deepest) category
        category = ""
        if categories:
            # Prefer child categories over parent
            category = categories[-1].get("slug", "") if categories else ""

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
