"""
Scraper for Biomateriales (biomateriales.cl)
Platform: Jumpseller
Products: Bone grafts, membranes, surgical instruments, implant-related products
Prices: CLP, publicly visible
"""
from __future__ import annotations

import re
import json
import time
import random
import logging
from typing import Optional, List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BiomaterialesScraper(BaseScraper):
    name = "Biomateriales"
    base_url = "https://www.biomateriales.cl"
    website_url = "https://www.biomateriales.cl"

    def scrape(self) -> List[Dict]:
        """Scrape all products using embedded JSON data from collection pages."""
        all_products = []
        page = 1

        while page <= 50:
            url = f"{self.base_url}/collection/todos-los-productos"
            if page > 1:
                url = f"{url}?page={page}"

            try:
                time.sleep(random.uniform(1, 3))
                response = self.session.get(url, timeout=30)
                if response.status_code != 200:
                    break

                # Extract window.INIT.collections JSON from page source
                match = re.search(
                    r'window\.INIT\.collections\s*=\s*(\[.*?\])\s*;',
                    response.text,
                    re.DOTALL,
                )
                if not match:
                    # Fallback: try HTML parsing
                    products = self._scrape_html(response.text)
                    if not products:
                        break
                    all_products.extend(products)
                    # Check if we got a full page
                    if len(products) < 24:
                        break
                    page += 1
                    continue

                data = json.loads(match.group(1))
                if not data:
                    break

                found = 0
                for product in data:
                    try:
                        item = self._parse_json_product(product)
                        if item:
                            all_products.append(item)
                            found += 1
                    except Exception as e:
                        logger.warning(f"[{self.name}] Error parsing: {e}")
                        continue

                print(f"  [{self.name}] Page {page}: {found} products (total: {len(all_products)})")

                if len(data) < 24:
                    break

                page += 1

            except Exception as e:
                logger.error(f"[{self.name}] Error on page {page}: {e}")
                break

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_json_product(self, p: dict) -> Optional[Dict]:
        """Parse a product from the window.INIT.collections JSON."""
        name = (p.get("title") or "").strip()
        if not name:
            return None

        price = p.get("finalPrice", 0)
        if not isinstance(price, (int, float)) or price <= 0:
            return None

        price = int(price)

        link = p.get("link", "")
        if link and not link.startswith("http"):
            link = f"{self.base_url}{link}"

        total_stock = p.get("totalStock", 0)
        allow_negative = p.get("allowNegativeStock", 0)
        in_stock = total_stock > 0 or allow_negative == 1

        image_url = p.get("defaultImage", "")

        brand_data = p.get("brand")
        brand = ""
        if isinstance(brand_data, dict):
            brand = brand_data.get("name", "")

        result = {
            "name": name,
            "price": price,
            "product_url": link,
            "in_stock": in_stock,
        }
        if image_url:
            result["image_url"] = image_url
        if brand:
            result["brand"] = brand

        return result

    def _scrape_html(self, html: str) -> List[Dict]:
        """Fallback: parse products from HTML (Jumpseller product-block divs)."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        products = []

        for el in soup.select("div.product-block"):
            try:
                name_el = el.select_one("a.product-block__name")
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if not name:
                    continue

                link = name_el.get("href", "")
                if link and not link.startswith("http"):
                    link = f"{self.base_url}{link}"

                price = 0
                price_el = el.select_one("div.product-block__price")
                if price_el:
                    price = self._parse_clp(price_el.get_text())

                if price <= 0:
                    form_el = el.select_one("form[data-price]")
                    if form_el:
                        price = self._parse_clp(form_el.get("data-price", ""))

                if price <= 0:
                    continue

                in_stock = True
                stock_input = el.select_one("input.product-block__input[data-stock]")
                if stock_input:
                    try:
                        in_stock = int(stock_input.get("data-stock", "1")) > 0
                    except ValueError:
                        pass

                brand_el = el.select_one("span.product-block__brand")
                brand = brand_el.get_text(strip=True) if brand_el else ""

                image_url = ""
                img_el = el.select_one("img.product-block__image, img")
                if img_el:
                    image_url = img_el.get("data-src") or img_el.get("src") or ""
                    if image_url and not image_url.startswith("http"):
                        image_url = f"{self.base_url}{image_url}"
                    if image_url.startswith("data:"):
                        image_url = ""

                result = {
                    "name": name,
                    "price": price,
                    "product_url": link,
                    "in_stock": in_stock,
                }
                if image_url:
                    result["image_url"] = image_url
                if brand:
                    result["brand"] = brand

                products.append(result)
            except Exception:
                continue

        return products

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price like '$229.000' to integer 229000."""
        if not text:
            return 0
        match = re.search(r'\$[\d.]+', text)
        if not match:
            return 0
        cleaned = match.group().replace('$', '').replace('.', '')
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test the scraper."""
        try:
            response = self.session.get(
                f"{self.base_url}/collection/todos-los-productos",
                timeout=15,
            )
            if response.status_code != 200:
                print(f"ERROR: {self.name} returned {response.status_code}")
                return False

            # Check for JSON data or HTML products
            has_json = "window.INIT.collections" in response.text
            has_html = "product-block" in response.text
            print(f"OK: {self.name} page loaded (JSON={has_json}, HTML={has_html})")
            return has_json or has_html
        except Exception as e:
            print(f"ERROR: {self.name} failed: {e}")
            return False
