"""
Scraper for Curaprox Chile (curaprox.cl)
Platform: PrestaShop (Classic-Rocket theme)
Products: Toothbrushes, toothpaste, interdental brushes, mouthwash, kids dental care
Prices: CLP, publicly visible
Brand: Curaprox (all products are Curaprox brand)
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict
from base_scraper import BaseScraper


class CuraproxScraper(BaseScraper):
    name = "Curaprox Chile"
    base_url = "https://curaprox.cl"
    website_url = "https://curaprox.cl"

    # PrestaShop category URLs (SEO-friendly slugs)
    categories = [
        # Toothbrushes
        "cepillos-de-dientes/cepillos-de-dientes-manuales",
        "cepillos-de-dientes/cepillos-electricos",
        "cepillos-de-dientes/cepillos-de-dientes-para-bebes-y-ninos",
        "cepillos-de-dientes/cepillos-de-dientes-especializados",
        # Toothpaste & mouthwash
        "pastas-de-dientes-y-colutorios/pasta-de-dientes-diaria",
        "pastas-de-dientes-y-colutorios/pasta-de-dientes-para-bebes-y-ninos",
        "pastas-de-dientes-y-colutorios/pasta-de-dientes-y-colutorio-especializados",
        # Interdental
        "espacios-interdentales/cepillos-interdentales",
        "espacios-interdentales/cepillos-interdentales-especializados",
        "espacios-interdentales/hilo-dental-y-palillo-de-dientes",
        # Baby & kids
        "bebes-y-ninos/chupetes-y-mordedores",
    ]

    # Map Curaprox categories to our standard categories
    CATEGORY_LABELS = {
        "cepillos-de-dientes/cepillos-de-dientes-manuales": "cepillos-manuales",
        "cepillos-de-dientes/cepillos-electricos": "cepillos-electricos",
        "cepillos-de-dientes/cepillos-de-dientes-para-bebes-y-ninos": "cepillos-infantiles",
        "cepillos-de-dientes/cepillos-de-dientes-especializados": "cepillos-especializados",
        "pastas-de-dientes-y-colutorios/pasta-de-dientes-diaria": "pasta-dental",
        "pastas-de-dientes-y-colutorios/pasta-de-dientes-para-bebes-y-ninos": "pasta-dental-infantil",
        "pastas-de-dientes-y-colutorios/pasta-de-dientes-y-colutorio-especializados": "pasta-colutorio-especializado",
        "espacios-interdentales/cepillos-interdentales": "cepillos-interdentales",
        "espacios-interdentales/cepillos-interdentales-especializados": "cepillos-interdentales-especializados",
        "espacios-interdentales/hilo-dental-y-palillo-de-dientes": "hilo-dental",
        "bebes-y-ninos/chupetes-y-mordedores": "chupetes-mordedores",
    }

    def scrape(self) -> List[Dict]:
        """Scrape all products from Curaprox PrestaShop categories."""
        all_products = []
        seen_urls = set()

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

                products = soup.select("article.product-miniature")
                if not products:
                    break

                found = 0
                for el in products:
                    try:
                        item = self._parse_product(el, category)
                        if item and item["product_url"] not in seen_urls:
                            seen_urls.add(item["product_url"])
                            all_products.append(item)
                            found += 1
                    except Exception as e:
                        print(f"  Error parsing Curaprox product: {e}")
                        continue

                if found == 0:
                    break

                # Check for next page
                next_link = soup.select_one("a.next, .pagination .next a, a[rel='next']")
                if not next_link or not next_link.get("href"):
                    break

                page += 1

            label = self.CATEGORY_LABELS.get(category, category.split("/")[-1])
            cat_count = len([p for p in all_products if p.get("_category") == self.CATEGORY_LABELS.get(category, category)])
            print(f"  [{label}] Found {cat_count} products")

        print(f"  Total: {len(all_products)} products from {self.name}")
        return all_products

    def _parse_product(self, el, category: str = "") -> Optional[Dict]:
        """Parse a Curaprox PrestaShop product-miniature article.

        Curaprox uses a Classic-Rocket theme where:
        - Product title is in <p class="h5 product-title"> (no <a> inside)
        - Product link is <a class="box-link"> covering the card
        - Price format is "14.225 $" (number before $)
        - Price span is <span class="current-price-display price">
        """
        # Product name — Curaprox uses <p class="product-title"> without inner <a>
        title_el = el.select_one(".product-title")
        if not title_el:
            return None

        name = title_el.get_text(strip=True)
        if not name:
            return None

        # Product URL — from .box-link or fallback to first <a>
        link_el = el.select_one("a.box-link") or el.select_one("a[href]")
        product_url = link_el.get("href", "") if link_el else ""
        if product_url and not product_url.startswith("http"):
            product_url = f"{self.base_url}{product_url}"

        # Price — Curaprox shows "14.225 $" format
        price = 0
        price_el = el.select_one("span.current-price-display, span.price, .current-price span")
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

        # Original price (if on sale)
        original_price = None
        regular_el = el.select_one(".regular-price, span.regular-price")
        if regular_el:
            orig = self._parse_clp(regular_el.get_text(strip=True))
            if orig > price:
                original_price = orig

        # Stock — assume in stock unless explicitly marked otherwise
        in_stock = True
        stock_el = el.select_one(".product-availability")
        if stock_el:
            stock_text = stock_el.get_text(strip=True).lower()
            if "agotado" in stock_text or "out of stock" in stock_text or "no disponible" in stock_text:
                in_stock = False

        # Product image
        image_url = ""
        img_el = el.select_one("img.lazyload, img.product-thumbnail-first, img")
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src") or ""
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.base_url}{image_url}"

        cat_label = self.CATEGORY_LABELS.get(category, category)

        result: Dict = {
            "name": name,
            "price": price,
            "product_url": product_url,
            "in_stock": in_stock,
            "brand": "Curaprox",
            "_category": cat_label,
        }
        if original_price:
            result["original_price"] = original_price
        if image_url:
            result["image_url"] = image_url

        return result

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price from PrestaShop format like '$6.340'."""
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
        """Test the scraper connectivity."""
        soup = self.fetch(f"{self.base_url}/{self.categories[0]}")
        if not soup:
            print(f"ERROR: Could not fetch {self.name}")
            return False

        products = soup.select("article.product-miniature")
        print(f"OK: Found {len(products)} product elements on {self.name}")
        return len(products) > 0
