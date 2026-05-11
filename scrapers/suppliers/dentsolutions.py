"""
Scraper for Dentsolutions (dentsolutions.cl)
Platform: Jumpseller
Products: Endodontics, orthodontics, composites, instruments, etc.
Prices: CLP, publicly visible
Location: Temuco, Chile
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class DentsolutionsScraper(BaseScraper):
    name = "Dentsolutions"
    base_url = "https://dentsolutions.cl"
    website_url = "https://dentsolutions.cl"

    # Jumpseller category slugs
    categories = [
        "anestesia",
        "blanqueamiento",
        "endodoncia",
        "instrumental",
        "ortodoncia",
        "prevencion",
        "operatoria",
    ]

    def scrape(self) -> List[Dict]:
        """Scrape all products from Dentsolutions."""
        all_products = []

        for category in self.categories:
            page = 1
            while True:
                url = f"{self.base_url}/{category}"
                if page > 1:
                    url = f"{self.base_url}/{category}?page={page}"

                soup = self.fetch(url)
                if not soup:
                    break

                # Jumpseller container element: was <div> pre-2026-04-29, now
                # <article>. Plain class selector is element-agnostic and
                # tokenized so "product-block__price" is NOT matched.
                products = soup.select(".product-block.product-block-product-feed")

                if not products:
                    break

                found_on_page = 0
                for product_el in products:
                    try:
                        item = self._parse_product(product_el, category)
                        if item:
                            all_products.append(item)
                            found_on_page += 1
                    except Exception as e:
                        print(f"  Error parsing product: {e}")
                        continue

                if found_on_page == 0:
                    break

                # Check for next page
                next_link = soup.select_one("a[rel='next'], .pagination .next a")
                if not next_link or not next_link.get("href"):
                    break

                page += 1

            cat_count = len([p for p in all_products if p.get("_category") == category])
            print(f"  [{category}] Found {cat_count} products")

        return all_products

    def _parse_product(self, el, category: str) -> Optional[Dict]:
        """Parse a single Jumpseller product-block."""
        # Product name from product-block__name
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

        # Price from product-block__price div
        price = 0
        price_el = el.select_one("div.product-block__price")
        if price_el:
            price_text = price_el.get_text(strip=True)
            price = self._parse_clp(price_text)

        # Also check the form data-price attribute as fallback
        if price <= 0:
            form_el = el.select_one("form[data-price]")
            if form_el:
                price = self._parse_clp(form_el.get("data-price", ""))

        if price <= 0:
            return None

        # Stock from input data-stock
        in_stock = True
        stock_input = el.select_one("input.product-block__input[data-stock]")
        if stock_input:
            stock_val = stock_input.get("data-stock", "1")
            try:
                in_stock = int(stock_val) > 0
            except ValueError:
                pass

        # Product image
        image_url = ""
        img_el = el.select_one("img.product-block__image, img")
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.base_url}{image_url}"

        result = {
            "name": name,
            "brand": brand,
            "price": price,
            "product_url": link,
            "in_stock": in_stock,
            "_category": category,
        }
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price like '$4.850' or '$36.900' to integer."""
        if not text:
            return 0
        # Extract just the price pattern: $ followed by digits and dots
        match = re.search(r'\$[\d.]+', text)
        if not match:
            return 0
        price_str = match.group()
        # Remove $ and dots (thousands separator in CLP)
        cleaned = price_str.replace('$', '').replace('.', '')
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test the scraper can find products."""
        soup = self.fetch(f"{self.base_url}/endodoncia")
        if not soup:
            print("ERROR: Could not fetch Dentsolutions")
            return False

        products = soup.select(".product-block.product-block-product-feed")
        print(f"OK: Found {len(products)} product elements on endodoncia page")
        return len(products) > 0
