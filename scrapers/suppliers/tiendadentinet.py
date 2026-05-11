"""
Scraper for Tienda Dentinet (tiendadentinet.com)
Platform: Jumpseller
Products: Composites, endodontics, surgery, anesthesia, whitening, equipment, etc.
Prices: CLP, publicly visible
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class TiendaDentinetScraper(BaseScraper):
    name = "Tienda Dentinet"
    base_url = "https://www.tiendadentinet.com"
    website_url = "https://www.tiendadentinet.com"

    # Jumpseller category slugs (from sitemap)
    categories = [
        "acondicionador-de-tejidos",
        "acrilico-dental",
        "adhesivo-dental",
        "aislacion",
        "anestesia",
        "biologicos",
        "blanqueamiento-dental",
        "cirugia-2",
        "cementos",
        "composites",
        "conos-de-gutapercha",
        "conos-de-papel",
        "descartables",
        "elementos-de-proteccion-personal",
        "equipamiento-odontologico",
        "esterilizacion",
        "fluor-barniz",
    ]

    def scrape(self) -> List[Dict]:
        """Scrape all products from Tienda Dentinet."""
        all_products = []
        seen_urls = set()

        for category in self.categories:
            page = 1
            while True:
                url = f"{self.base_url}/{category}"
                if page > 1:
                    url = f"{url}?page={page}"

                soup = self.fetch(url)
                if not soup:
                    break

                products = soup.select("div.product-block")
                if not products:
                    break

                found_on_page = 0
                for product_el in products:
                    try:
                        item = self._parse_product(product_el, category)
                        if item and item["product_url"] not in seen_urls:
                            all_products.append(item)
                            seen_urls.add(item["product_url"])
                            found_on_page += 1
                    except Exception as e:
                        print(f"  Error parsing product: {e}")
                        continue

                if found_on_page == 0:
                    break

                # Check for next page
                next_link = soup.select_one("a[rel='next'], .pagination .next a")
                if not next_link or not next_link.get("href"):
                    # Also check if page returned fewer products (no explicit next link)
                    if len(products) < 40:
                        break
                    page += 1
                    continue

                page += 1

            cat_count = len([p for p in all_products if p.get("_category") == category])
            print(f"  [{category}] Found {cat_count} products")

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, el, category: str) -> Optional[Dict]:
        """Parse a single Jumpseller product-block."""
        name_el = el.select_one("a.product-block__name")
        if not name_el:
            return None

        name = name_el.get_text(strip=True)
        if not name:
            return None

        # Product URL
        link = name_el.get("href", "")
        if link and not link.startswith("http"):
            link = f"{self.base_url}{link}"

        # Brand
        brand_el = el.select_one("span.product-block__brand")
        brand = brand_el.get_text(strip=True) if brand_el else None

        # Price
        price = 0
        price_el = el.select_one("div.product-block__price")
        if price_el:
            price_text = price_el.get_text(strip=True)
            price = self._parse_clp(price_text)

        # Fallback: form data-price attribute
        if price <= 0:
            form_el = el.select_one("form[data-price]")
            if form_el:
                price = self._parse_clp(form_el.get("data-price", ""))

        if price <= 0:
            return None

        # Stock
        in_stock = True
        stock_input = el.select_one("input.product-block__input[data-stock]")
        if stock_input:
            stock_val = stock_input.get("data-stock", "1")
            try:
                in_stock = int(stock_val) > 0
            except ValueError:
                pass

        # Image
        image_url = ""
        img_el = el.select_one("img.product-block__image, img")
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.base_url}{image_url}"

        result = {
            "name": name,
            "price": price,
            "product_url": link,
            "in_stock": in_stock,
            "_category": category,
        }
        if brand:
            result["brand"] = brand
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price like '$17.500' to integer 17500."""
        if not text:
            return 0
        match = re.search(r'\$[\d.]+', text)
        if not match:
            return 0
        price_str = match.group()
        cleaned = price_str.replace('$', '').replace('.', '')
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test the scraper can find products."""
        soup = self.fetch(f"{self.base_url}/composites")
        if not soup:
            print("ERROR: Could not fetch Tienda Dentinet")
            return False

        products = soup.select("div.product-block")
        print(f"OK: Found {len(products)} product elements on composites page")
        return len(products) > 0
