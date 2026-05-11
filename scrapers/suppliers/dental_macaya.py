"""
Scraper for Dental Macaya (dentalmacaya.cl)
Platform: WooCommerce (WordPress)
Products: Equipment, instruments, consumables
Prices: CLP, publicly visible
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class DentalMacayaScraper(BaseScraper):
    name = "Dental Macaya"
    base_url = "https://dentalmacaya.cl"
    website_url = "https://dentalmacaya.cl"
    use_playwright_stealth = True

    def scrape(self) -> List[Dict]:
        """Scrape all products from Dental Macaya store."""
        all_products = []
        page = 1

        while True:
            url = f"{self.base_url}/shop/page/{page}/" if page > 1 else f"{self.base_url}/shop/"
            soup = self.fetch(url)
            if not soup:
                break

            products = soup.select("li.product")
            if not products:
                break

            for product_el in products:
                try:
                    item = self._parse_product(product_el)
                    if item:
                        all_products.append(item)
                except Exception as e:
                    print(f"  Error parsing product: {e}")
                    continue

            next_link = soup.select_one("a.next.page-numbers")
            if not next_link:
                break
            page += 1

        print(f"  Total: {len(all_products)} products from Dental Macaya")
        return all_products

    def _parse_product(self, el) -> Optional[Dict]:
        """Parse a WooCommerce product card."""
        name_el = (
            el.select_one("h3.woocommerce-loop-product__title")
            or el.select_one("h2.woocommerce-loop-product__title")
            or el.select_one("h3")
            or el.select_one("h2")
        )
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        link_el = el.select_one("a.woocommerce-LoopProduct-link") or el.select_one("a")
        product_url = link_el["href"] if link_el and link_el.get("href") else ""

        price = 0
        sale_price_el = el.select_one("ins .woocommerce-Price-amount")
        if sale_price_el:
            price = self._parse_clp(sale_price_el.get_text())
        else:
            price_el = el.select_one(".woocommerce-Price-amount")
            if price_el:
                price = self._parse_clp(price_el.get_text())

        if price <= 0:
            return None

        in_stock = not bool(el.select_one(".outofstock, .out-of-stock"))

        # Product image
        image_url = ""
        img_el = el.select_one("img.attachment-woocommerce_thumbnail, img.wp-post-image, img")
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            if image_url.startswith("data:"):
                image_url = img_el.get("data-src") or img_el.get("data-lazy-src") or ""

        result = {
            "name": name,
            "price": price,
            "product_url": product_url,
            "in_stock": in_stock,
        }
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_clp(self, text: str) -> int:
        if not text:
            return 0
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        soup = self.fetch(f"{self.base_url}/shop/")
        if not soup:
            print("ERROR: Could not fetch Dental Macaya")
            return False
        products = soup.select("li.product, div.product")
        print(f"OK: Found {len(products)} product elements")
        return len(products) > 0
