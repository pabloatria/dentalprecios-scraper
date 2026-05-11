"""
Generic WooCommerce scraper that works with most WooCommerce stores.
Configurable via class attributes for each specific store.
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class WooGenericScraper(BaseScraper):
    """Generic WooCommerce scraper. Subclass and set class attributes."""

    name = "WooGeneric"
    base_url = ""
    website_url = ""

    # Override in subclass: list of category slugs
    categories: List[str] = []

    # URL pattern: "product-category" or "tienda" based pagination
    # If categories is empty, uses shop_url for flat pagination
    category_url_pattern = "/product-category/{category}/"
    shop_url = "/tienda/"

    # Pagination pattern: "page/{n}/" (WooCommerce default) or "?paged={n}"
    pagination_style = "path"  # "path" = /page/2/, "query" = ?paged=2

    # CSS selectors (WooCommerce defaults - override if needed)
    product_selector = "li.product"
    title_selectors = [
        "h2.woocommerce-loop-product__title",
        "h3.woocommerce-loop-product__title",
        "h2",
        "h3",
    ]
    link_selector = "a.woocommerce-LoopProduct-link"
    sale_price_selector = "ins .woocommerce-Price-amount"
    regular_price_selector = ".woocommerce-Price-amount"
    outofstock_selector = ".outofstock, .out-of-stock"
    next_page_selector = "a.next, a.woocommerce-pagination__next, .next.page-numbers"

    def scrape(self) -> List[Dict]:
        """Scrape all products."""
        all_products = []

        if self.categories:
            for category in self.categories:
                cat_products = self._scrape_category(category)
                all_products.extend(cat_products)
                print(f"  [{category}] Found {len(cat_products)} products")
        else:
            all_products = self._scrape_paginated(self.shop_url)

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _scrape_category(self, category: str) -> List[Dict]:
        """Scrape all pages of a category."""
        products = []
        page = 1

        while True:
            if page == 1:
                url = f"{self.base_url}{self.category_url_pattern.format(category=category)}"
            else:
                base = f"{self.base_url}{self.category_url_pattern.format(category=category)}"
                if self.pagination_style == "path":
                    url = f"{base}page/{page}/"
                else:
                    sep = "&" if "?" in base else "?"
                    url = f"{base}{sep}paged={page}"

            soup = self.fetch(url)
            if not soup:
                break

            items = soup.select(self.product_selector)
            if not items:
                break

            found = 0
            for el in items:
                try:
                    item = self._parse_product(el, category)
                    if item:
                        products.append(item)
                        found += 1
                except Exception as e:
                    print(f"  Error parsing product: {e}")
                    continue

            if found == 0:
                break

            next_link = soup.select_one(self.next_page_selector)
            if not next_link:
                break

            page += 1

        return products

    def _scrape_paginated(self, path: str) -> List[Dict]:
        """Scrape paginated shop page (no categories)."""
        products = []
        page = 1

        while True:
            if page == 1:
                url = f"{self.base_url}{path}"
            else:
                if self.pagination_style == "path":
                    url = f"{self.base_url}{path}page/{page}/"
                else:
                    sep = "&" if "?" in path else "?"
                    url = f"{self.base_url}{path}{sep}paged={page}"

            soup = self.fetch(url)
            if not soup:
                break

            items = soup.select(self.product_selector)
            if not items:
                break

            found = 0
            for el in items:
                try:
                    item = self._parse_product(el)
                    if item:
                        products.append(item)
                        found += 1
                except Exception as e:
                    print(f"  Error parsing product: {e}")
                    continue

            if found == 0:
                break

            next_link = soup.select_one(self.next_page_selector)
            if not next_link:
                break

            page += 1

        return products

    def _parse_product(self, el, category: str = "") -> Optional[Dict]:
        """Parse a standard WooCommerce product card."""
        # Product name
        name_el = None
        for sel in self.title_selectors:
            name_el = el.select_one(sel)
            if name_el:
                break
        if not name_el:
            return None

        name = name_el.get_text(strip=True)
        if not name:
            return None

        # Product URL
        link_el = el.select_one(self.link_selector) or el.select_one("a")
        product_url = link_el["href"] if link_el and link_el.get("href") else ""

        # Price (prefer sale price)
        price = 0
        original_price = None
        sale_el = el.select_one(self.sale_price_selector)
        if sale_el:
            price = self._parse_clp(sale_el.get_text())
            # Grab struck-through regular price (<del> element)
            del_el = el.select_one("del .woocommerce-Price-amount, del .amount")
            if del_el:
                parsed_original = self._parse_clp(del_el.get_text())
                if parsed_original > price:
                    original_price = parsed_original
        else:
            price_el = el.select_one(self.regular_price_selector)
            if price_el:
                price = self._parse_clp(price_el.get_text())

        if price <= 0:
            return None

        # Stock
        in_stock = not bool(el.select_one(self.outofstock_selector))

        # Product image
        image_url = ""
        img_el = el.select_one("img.attachment-woocommerce_thumbnail, img.wp-post-image, img")
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            # Skip placeholder/lazy-load data URIs
            if image_url.startswith("data:"):
                image_url = img_el.get("data-src") or img_el.get("data-lazy-src") or ""

        result = {
            "name": name,
            "price": price,
            "product_url": product_url,
            "in_stock": in_stock,
        }
        if original_price:
            result["original_price"] = original_price
        if category:
            result["_category"] = category
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price like '$29.970' to integer 29970."""
        if not text:
            return 0
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test the scraper can find products."""
        if self.categories:
            url = f"{self.base_url}{self.category_url_pattern.format(category=self.categories[0])}"
        else:
            url = f"{self.base_url}{self.shop_url}"

        soup = self.fetch(url)
        if not soup:
            print(f"ERROR: Could not fetch {self.name}")
            return False

        products = soup.select(self.product_selector)
        print(f"OK: Found {len(products)} product elements on {self.name}")
        return len(products) > 0
