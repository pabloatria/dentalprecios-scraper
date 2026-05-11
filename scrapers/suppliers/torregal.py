"""
Scraper for Torregal (torregal.cl)
Platform: WordPress + The7 Theme — uses WP REST API (dt_portfolio custom post type)
Products: Medical aesthetic equipment (lasers, body contouring, etc.)
Prices: NONE — catalog-only (price=0). Contact supplier for pricing.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class TorregalScraper(BaseScraper):
    name = "Torregal"
    base_url = "https://torregal.cl"
    website_url = "https://www.torregal.cl"

    api_url = "https://torregal.cl/wp-json/wp/v2/dt_portfolio"
    categories_url = "https://torregal.cl/wp-json/wp/v2/dt_portfolio_category"

    def scrape(self) -> List[Dict]:
        """Scrape all products via WP REST API (catalog-only, no prices)."""
        # Fetch brand categories first
        brand_map = {}
        try:
            response = self.session.get(
                self.categories_url,
                params={"per_page": 100},
                timeout=30,
            )
            if response.status_code == 200:
                for cat in response.json():
                    brand_map[cat["id"]] = cat["name"]
        except Exception as e:
            logger.warning(f"[{self.name}] Could not fetch categories: {e}")

        all_products = []
        page = 1

        while page <= 5:
            try:
                response = self.session.get(
                    self.api_url,
                    params={
                        "per_page": 100,
                        "page": page,
                        "_embed": "",
                    },
                    timeout=30,
                )
                if response.status_code != 200:
                    break

                data = response.json()
                if not isinstance(data, list) or not data:
                    break

                for product in data:
                    try:
                        item = self._parse_product(product, brand_map)
                        if item:
                            all_products.append(item)
                    except Exception as e:
                        logger.warning(f"[{self.name}] Error parsing: {e}")
                        continue

                print(f"  [{self.name}] Page {page}: {len(data)} products (total: {len(all_products)})")

                if len(data) < 100:
                    break

                page += 1

            except Exception as e:
                logger.error(f"[{self.name}] API error page {page}: {e}")
                break

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, product: dict, brand_map: dict) -> Optional[Dict]:
        """Parse a WP REST API portfolio item."""
        title = product.get("title", {}).get("rendered", "").strip()
        if not title:
            return None

        permalink = product.get("link", "")

        # Get featured image from _embedded
        image_url = ""
        embedded = product.get("_embedded", {})
        featured_media = embedded.get("wp:featuredmedia", [])
        if featured_media and isinstance(featured_media, list) and len(featured_media) > 0:
            image_url = featured_media[0].get("source_url", "")

        # Get brand from portfolio categories
        cat_ids = product.get("dt_portfolio_category", [])
        brand = ""
        if cat_ids and cat_ids[0] in brand_map:
            brand = brand_map[cat_ids[0]]

        result = {
            "name": title,
            "price": 0,  # Catalog-only — no prices available
            "product_url": permalink,
            "in_stock": True,
            "_category": "estetica-equipos",  # All Torregal products are aesthetic equipment
        }
        if image_url:
            result["image_url"] = image_url
        if brand:
            result["brand"] = brand

        return result

    def test(self) -> bool:
        """Test the WP REST API."""
        try:
            response = self.session.get(
                self.api_url,
                params={"per_page": 3},
                timeout=15,
            )
            if response.status_code != 200:
                print(f"ERROR: {self.name} API returned {response.status_code}")
                return False

            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            print(f"OK: Found {count} products via WP API on {self.name}")
            return count > 0
        except Exception as e:
            print(f"ERROR: {self.name} API failed: {e}")
            return False
