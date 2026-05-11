"""
Scraper for SuperDental (www.superdental.cl)
Platform: WordPress + WooCommerce + Elementor
Products: Full range dental supplies
Prices: CLP, publicly visible
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class SuperDentalScraper(BaseScraper):
    name = "SuperDental"
    base_url = "https://www.superdental.cl"
    website_url = "https://www.superdental.cl"

    # WooCommerce category pages
    categories = [
        "adhesion-y-restauracion",
        "anestesicos-y-agujas",
        "barnices-y-fluor",
        "blanqueamiento-y-barreras",
        "desechables",
        "desinfeccion-y-bioseguridad",
        "endodoncia",
        "equipamiento",
        "fresas",
        "higiene-oral",
        "impresion-y-rehabilitacion",
        "instrumental",
        "laboratorio",
        "ortodoncia",
        "periodoncia-y-cirugia",
        "protesis-y-carillas",
        "radiologia",
    ]

    def scrape(self) -> List[Dict]:
        """Scrape all products from SuperDental."""
        all_products = []

        for category in self.categories:
            page = 1
            while True:
                url = f"{self.base_url}/product-category/{category}/page/{page}/"
                if page == 1:
                    url = f"{self.base_url}/product-category/{category}/"

                soup = self.fetch(url)
                if not soup:
                    break

                # WooCommerce product list items
                products = soup.select("li.product, div.product, .wc-block-grid__product")

                # Also try Elementor product widget cards
                if not products:
                    products = soup.select("[class*='elementor-widget-wc-archive-products'] li")

                if not products:
                    break

                for product_el in products:
                    try:
                        item = self._parse_product(product_el, category)
                        if item:
                            all_products.append(item)
                    except Exception as e:
                        print(f"  Error parsing product: {e}")
                        continue

                # Check for next page
                next_link = soup.select_one("a.next, a.woocommerce-pagination__next, .next.page-numbers")
                if not next_link:
                    break

                page += 1

            print(f"  [{category}] Found {len([p for p in all_products if p.get('_category') == category])} products")

        return all_products

    def _parse_product(self, el, category: str) -> Optional[Dict]:
        """Parse a single product element."""
        # Product name - try multiple selectors
        name_el = (
            el.select_one("h2.woocommerce-loop-product__title")
            or el.select_one(".wc-block-grid__product-title")
            or el.select_one("h2")
            or el.select_one("[class*='product-title'] a")
            or el.select_one("a.woocommerce-LoopProduct-link h2")
        )
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        # Product URL
        link_el = (
            el.select_one("a.woocommerce-LoopProduct-link")
            or el.select_one("a[href*='/tienda/']")
            or el.select_one("h2 a")
            or el.select_one("a")
        )
        product_url = link_el["href"] if link_el and link_el.get("href") else ""

        # Price - get the current price (not the original/strikethrough)
        price = 0
        # Try sale price first (ins tag in WooCommerce)
        sale_price_el = el.select_one("ins .woocommerce-Price-amount, ins .amount")
        if sale_price_el:
            price = self._parse_clp(sale_price_el.get_text())
        else:
            # Regular price
            price_el = (
                el.select_one(".woocommerce-Price-amount")
                or el.select_one(".price .amount")
                or el.select_one("[class*='price']")
            )
            if price_el:
                price = self._parse_clp(price_el.get_text())

        if price <= 0:
            return None

        # Stock - assume in stock if listed
        in_stock = True
        outofstock = el.select_one(".outofstock, .out-of-stock")
        if outofstock:
            in_stock = False

        return {
            "name": name,
            "price": price,
            "product_url": product_url,
            "in_stock": in_stock,
            "_category": category,
        }

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price string like '$29.970' to integer 29970."""
        if not text:
            return 0
        # Remove currency symbol, dots (thousands separator), spaces
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test that the scraper can reach the site and find products."""
        soup = self.fetch(f"{self.base_url}/tienda/")
        if not soup:
            print("ERROR: Could not fetch SuperDental store page")
            return False

        products = soup.select("li.product, div.product, [class*='product']")
        print(f"OK: Found {len(products)} product elements on store page")
        return len(products) > 0
