"""
Scraper for Expro Dental (exprodental.cl)
Platform: Custom PHP site
Products: ~1,800 dental products (equipment, instruments, consumables)
Prices: CLP, publicly visible
Pagination: /productos.php?p=N&av=1 (10 products per page, ~181 pages)
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class ExproDentalScraper(BaseScraper):
    name = "Expro Dental"
    base_url = "https://www.exprodental.cl"
    website_url = "https://www.exprodental.cl"

    def scrape(self) -> List[Dict]:
        """Scrape all products from Expro Dental store."""
        all_products = []
        page = 1
        max_pages = 200  # Safety limit; site has ~181 pages
        consecutive_empty = 0

        while page <= max_pages:
            url = f"{self.base_url}/productos.php?p={page}&av=1"
            soup = self.fetch(url)
            if not soup:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                page += 1
                continue

            products = soup.select("div.prod")
            if not products:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                page += 1
                continue

            consecutive_empty = 0

            for product_el in products:
                try:
                    item = self._parse_product(product_el)
                    if item:
                        all_products.append(item)
                except Exception as e:
                    print(f"  Error parsing product on page {page}: {e}")
                    continue

            if page % 20 == 0:
                print(f"  Expro Dental: page {page}, {len(all_products)} products so far")

            page += 1

        print(f"  Total: {len(all_products)} products from Expro Dental")
        return all_products

    def _parse_product(self, el) -> Optional[Dict]:
        """Parse a product card from the custom PHP listing.

        HTML structure:
        <div class="prod">
            <span class="marca">Código: 4484</span>
            <figcaption>
                <a href="producto/...">
                    <img src="imagenes/productos/166x147/4484.jpg" alt="Product Name"/>
                </a>
            </figcaption>
            <article>
                <p class="info-p">BRAND</p>
                <a href="producto/..."><h4><strong>Product Name</strong></h4></a>
                <p class="info-p">Precio Internet</p>
                <p class="precio">$57.990.000.-</p>
                <a href="#" class="agregar" data-id="3675">Agregar al carro</a>
                  -- OR --
                <a class="agregar sinstock">Sin stock</a>
            </article>
        </div>
        """
        # Product name from h4 inside article
        name_el = el.select_one("article h4 strong") or el.select_one("article h4")
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        # Product URL from the link wrapping the h4
        product_url = ""
        link_el = el.select_one("article a[href*='producto/']")
        if link_el and link_el.get("href"):
            href = link_el["href"]
            if not href.startswith("http"):
                product_url = f"{self.base_url}/{href.lstrip('/')}"
            else:
                product_url = href

        # Price
        price = 0
        price_el = el.select_one("p.precio")
        if price_el:
            price = self._parse_clp(price_el.get_text())

        if price <= 0:
            return None

        # Stock status: "Sin stock" appears as <a class="agregar sinstock">
        in_stock = True
        stock_el = el.select_one("a.agregar.sinstock, a.sinstock")
        if stock_el:
            in_stock = False

        # Image URL
        image_url = ""
        img_el = el.select_one("figcaption img")
        if img_el:
            src = img_el.get("src", "")
            if src and not src.startswith("http"):
                image_url = f"{self.base_url}/{src.lstrip('/')}"
            else:
                image_url = src

        # Brand from first <p class="info-p"> inside article
        brand = ""
        info_ps = el.select("article p.info-p")
        if info_ps:
            brand_text = info_ps[0].get_text(strip=True)
            # The first info-p is the brand, the second is "Precio Internet"
            if brand_text and brand_text.lower() != "precio internet":
                brand = brand_text

        result = {
            "name": name,
            "price": price,
            "product_url": product_url,
            "in_stock": in_stock,
        }
        if image_url:
            result["image_url"] = image_url
        if brand:
            result["brand"] = brand

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price string like '$57.990.000.-' to integer."""
        if not text:
            return 0
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test that the scraper can connect and parse page 1."""
        soup = self.fetch(f"{self.base_url}/productos.php?p=1&av=1")
        if not soup:
            print("ERROR: Could not fetch Expro Dental")
            return False
        products = soup.select("div.prod")
        print(f"OK: Found {len(products)} product elements on page 1")
        return len(products) > 0
