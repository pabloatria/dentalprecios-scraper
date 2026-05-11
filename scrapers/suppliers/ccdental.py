"""
Scraper for CC Dental Chile (ccdentalchile.cl)
Platform: Jumpseller
Products: Endodontics, instruments, general dentistry, simulation, imaging
Prices: CLP, publicly visible
Estimated: ~200-400 products
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class CCDentalScraper(BaseScraper):
    name = "CC Dental Chile"
    base_url = "https://www.ccdentalchile.cl"
    website_url = "https://www.ccdentalchile.cl"

    def scrape(self) -> List[Dict]:
        """Scrape all products from CC Dental Chile /tienda pages."""
        all_products = []
        seen_urls = set()
        page = 1

        while page <= 20:  # Safety cap
            url = f"{self.base_url}/tienda"
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
                    item = self._parse_product(product_el)
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
                # If fewer than expected products, assume last page
                if len(products) < 24:
                    break
                page += 1
                continue

            page += 1

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, el) -> Optional[Dict]:
        """Parse a single Jumpseller product-block."""
        # Product name
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

        # Price - check for sale price first
        price = 0
        original_price = None

        # Sale price: Jumpseller shows compare price (original) and current price
        compare_el = el.select_one(
            ".product-block__price--compare, "
            ".product-block__price--was, "
            ".product-block__compare-price"
        )
        current_price_el = el.select_one("div.product-block__price")

        if compare_el and current_price_el:
            original_price = self._parse_clp(compare_el.get_text())
            price = self._parse_clp(current_price_el.get_text())
            # Ensure original > current (sanity check)
            if original_price and price and original_price <= price:
                original_price = None
        elif current_price_el:
            price = self._parse_clp(current_price_el.get_text())

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

        # Also check for sold-out label
        sold_out_el = el.select_one(
            ".product-block__label--sold-out, "
            ".product-block__label--agotado"
        )
        if sold_out_el:
            in_stock = False

        # Image
        image_url = ""
        img_el = el.select_one("img.product-block__image, img")
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.base_url}{image_url}"
            if image_url.startswith("data:"):
                image_url = img_el.get("data-src") or img_el.get("data-lazy-src") or ""

        result = {
            "name": name,
            "price": price,
            "product_url": link,
            "in_stock": in_stock,
        }
        if brand:
            result["brand"] = brand
        if image_url:
            result["image_url"] = image_url
        if original_price and original_price > price:
            result["original_price"] = original_price

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price like '$55.900' or '$4.700 CLP' to integer."""
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
        """Test the scraper can find products on the store page."""
        soup = self.fetch(f"{self.base_url}/tienda")
        if not soup:
            print(f"ERROR: Could not fetch {self.name}")
            return False

        products = soup.select("div.product-block")
        print(f"OK: Found {len(products)} product elements on /tienda page")
        return len(products) > 0
