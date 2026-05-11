"""
Scraper for Biotech Chile (biotechchile.cl)
Platform: Odoo 18 (e-commerce module)
Products: Dental equipment, motors, endodontics, instruments
Prices: CLP, publicly visible
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class BiotechChileScraper(BaseScraper):
    name = "Biotech Chile"
    base_url = "https://www.biotechchile.cl"
    website_url = "https://www.biotechchile.cl"
    use_playwright_stealth = True

    max_pages = 50  # Safety limit

    def scrape(self) -> List[Dict]:
        """Scrape all products from Odoo shop."""
        all_products = []
        page = 1  # Odoo pages start at 1

        while page <= self.max_pages:
            if page == 1:
                url = f"{self.base_url}/shop"
            else:
                url = f"{self.base_url}/shop/page/{page}"

            soup = self.fetch(url)
            if not soup:
                break

            # Odoo product cards
            product_forms = soup.select("form.oe_product_cart, form.shop_card")
            if not product_forms:
                break

            found = 0
            for form in product_forms:
                try:
                    item = self._parse_product(form)
                    if item:
                        all_products.append(item)
                        found += 1
                except Exception as e:
                    print(f"  Error parsing product: {e}")
                    continue

            if found == 0:
                break

            # Check for next page: look for a link to a page number higher than current
            has_next = False
            page_links = soup.select("a.page-link[href*='/shop/page/']")
            for pl in page_links:
                href = pl.get("href", "")
                match = re.search(r'/page/(\d+)', href)
                if match:
                    pg = int(match.group(1))
                    if pg > page:
                        has_next = True
                        break

            if not has_next:
                break

            page += 1

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, form) -> Optional[Dict]:
        """Parse an Odoo product card form."""
        # Product name - from link or itemprop
        name = ""
        name_el = form.select_one("[itemprop='name']")
        if name_el:
            name = name_el.get_text(strip=True)

        if not name:
            # Try the product card link text
            link_el = form.select_one("a.product-card-modern__imagewrap, a[href*='/shop/']")
            if link_el:
                img_el = link_el.select_one("img")
                if img_el:
                    name = img_el.get("alt", "").strip()

        if not name:
            # Try finding any text that looks like a product name
            title_div = form.select_one(".product-card-modern__name, .o_wsale_product_information a")
            if title_div:
                name = title_div.get_text(strip=True)

        if not name:
            return None

        # Clean name - remove SKU prefix like [PACK1916]
        name = re.sub(r'^\[[\w]+\]\s*', '', name).strip()
        if not name:
            return None

        # Product URL
        product_url = ""
        link_el = form.select_one("a[href*='/shop/']")
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("/"):
                product_url = f"{self.base_url}{href}"
            else:
                product_url = href

        # Price from oe_currency_value
        price = 0
        price_el = form.select_one(".oe_currency_value")
        if price_el:
            price_text = price_el.get_text(strip=True)
            price = self._parse_clp(price_text)

        if price <= 0:
            return None

        # Brand
        brand_el = form.select_one(".product-card-modern__brand")
        brand = brand_el.get_text(strip=True) if brand_el else None

        # Product image
        image_url = ""
        img_el = form.select_one("img[itemprop='image'], img.product_detail_img, img")
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            if image_url and image_url.startswith("/"):
                image_url = f"{self.base_url}{image_url}"

        result = {
            "name": name,
            "price": price,
            "product_url": product_url,
            "in_stock": True,  # Assume in stock if listed
        }
        if brand:
            result["brand"] = brand
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price like '679.000' to integer 679000."""
        if not text:
            return 0
        # Remove dots (thousands separator) and any currency symbols
        cleaned = text.replace('.', '').replace('$', '').replace(' ', '').strip()
        # Remove any trailing decimals if present
        cleaned = cleaned.split(',')[0]
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test the scraper."""
        soup = self.fetch(f"{self.base_url}/shop")
        if not soup:
            print(f"ERROR: Could not fetch {self.name}")
            return False

        products = soup.select("form.oe_product_cart, form.shop_card")
        print(f"OK: Found {len(products)} product forms on {self.name}")
        return len(products) > 0
