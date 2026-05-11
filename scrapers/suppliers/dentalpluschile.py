"""
Scraper for Dental Plus Chile (dentalpluschile.cl)
Platform: PrestaShop
Products: Dental supplies — clinic, hygiene, endodontics, carbide, diamond, equipment, instruments, medical supplies, lab, rotary instruments
Prices: CLP, publicly visible
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class DentalPlusChileScraper(BaseScraper):
    name = "Dental Plus Chile"
    base_url = "https://dentalpluschile.cl"
    website_url = "https://dentalpluschile.cl"

    # PrestaShop category URLs: {id}-{slug}
    categories = [
        "4-clinica-dental",
        "171-higiene-dental",
        "6-endodoncia",
        "3-carbide",
        "5-diamante",
        "7-equipamiento",
        "8-instrumental",
        "9-insumos-medicos",
        "10-laboratorio",
        "11-instr-rotatorio",
    ]

    def scrape(self) -> List[Dict]:
        """Scrape all products from PrestaShop categories."""
        all_products = []

        for category in self.categories:
            page = 1
            while True:
                if page == 1:
                    url = f"{self.base_url}/{category}"
                else:
                    url = f"{self.base_url}/{category}?page={page}"

                soup = self.fetch(url)
                if not soup:
                    break

                products = soup.select(".product-miniature")
                if not products:
                    break

                found = 0
                for el in products:
                    try:
                        item = self._parse_product(el, category)
                        if item:
                            all_products.append(item)
                            found += 1
                    except Exception as e:
                        print(f"  Error parsing product: {e}")
                        continue

                if found == 0:
                    break

                # Check for next page
                next_link = soup.select_one("a.next, .pagination .next a, a[rel='next']")
                if not next_link or not next_link.get("href"):
                    break

                page += 1

            cat_name = category.split("-", 1)[1] if "-" in category else category
            cat_count = len([p for p in all_products if p.get("_category") == category])
            print(f"  [{cat_name}] Found {cat_count} products")

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, el, category: str = "") -> Optional[Dict]:
        """Parse a PrestaShop product-miniature element."""
        # Product name — h3 > a
        title_el = el.select_one("h3 a, .product-title a, h2 a")
        if not title_el:
            return None

        name = title_el.get_text(strip=True)
        if not name:
            return None

        # Product URL
        product_url = title_el.get("href", "")

        # Price
        price = 0
        price_el = el.select_one(".price, span.product-price, .product-price-and-shipping .price")
        if price_el:
            content = price_el.get("content", "")
            if content:
                try:
                    price = int(float(content))
                except (ValueError, TypeError):
                    price = self._parse_clp(price_el.get_text(strip=True))
            else:
                price = self._parse_clp(price_el.get_text(strip=True))

        if price <= 0:
            return None

        # Stock
        in_stock = True
        stock_el = el.select_one(".product-availability")
        if stock_el:
            stock_text = stock_el.get_text(strip=True).lower()
            if "agotado" in stock_text or "out of stock" in stock_text or "no disponible" in stock_text:
                in_stock = False

        # Product image
        image_url = ""
        img_el = el.select_one("img")
        if img_el:
            image_url = img_el.get("data-full-size-image-url") or img_el.get("data-src") or img_el.get("src") or ""
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.base_url}{image_url}"

        result = {
            "name": name,
            "price": price,
            "product_url": product_url,
            "in_stock": in_stock,
        }
        if category:
            result["_category"] = category
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price like '$ 4.590' to integer 4590."""
        if not text:
            return 0
        match = re.search(r'[\$]?\s*[\d.]+', text)
        if not match:
            return 0
        cleaned = match.group().replace('$', '').replace('.', '').replace(' ', '').strip()
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test the scraper."""
        soup = self.fetch(f"{self.base_url}/{self.categories[0]}")
        if not soup:
            print(f"ERROR: Could not fetch {self.name}")
            return False

        products = soup.select(".product-miniature")
        print(f"OK: Found {len(products)} product elements on {self.name}")
        return len(products) > 0
