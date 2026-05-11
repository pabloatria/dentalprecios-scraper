"""
Scraper for OdontoImport (odontoimport.cl)
Platform: Custom ASP.NET site
Products: ~1,000+ dental supplies, instruments, equipment
Prices: CLP, publicly visible
Strategy: Fetch sitemap.xml -> extract product URLs -> scrape each product page
         Uses JSON-LD structured data as primary source, HTML fallback for brand/original_price.
"""
from __future__ import annotations

import json
import re
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Non-product page patterns to skip from the sitemap
SKIP_PATTERNS = [
    "Producto_Listado.aspx",
    "Default.aspx",
    "Contacto.aspx",
    "Contacto_Distribuidor.aspx",
    "Clinicas.aspx",
    "Categoria-",
    "Subcategoria-",
]


class OdontoimportScraper(BaseScraper):
    name = "OdontoImport"
    base_url = "https://www.odontoimport.cl"
    website_url = "https://www.odontoimport.cl"

    SITEMAP_URL = "https://odontoimport.cl/docs/sitemap.xml"

    def scrape(self) -> List[Dict]:
        """Scrape all products from OdontoImport via sitemap discovery."""
        product_urls = self._get_product_urls()
        if not product_urls:
            logger.error(f"[{self.name}] No product URLs found in sitemap")
            return []

        logger.info(f"[{self.name}] Found {len(product_urls)} product URLs in sitemap")

        all_products = []
        errors = 0

        for i, url in enumerate(product_urls):
            if i > 0 and i % 50 == 0:
                logger.info(f"[{self.name}] Progress: {i}/{len(product_urls)} pages scraped, {len(all_products)} products found")

            try:
                product = self._scrape_product_page(url)
                if product:
                    all_products.append(product)
            except Exception as e:
                errors += 1
                logger.debug(f"[{self.name}] Error scraping {url}: {e}")
                if errors > 50:
                    logger.warning(f"[{self.name}] Too many errors ({errors}), stopping early")
                    break

        logger.info(f"[{self.name}] Total: {len(all_products)} products scraped ({errors} errors)")
        return all_products

    def _get_product_urls(self) -> List[str]:
        """Fetch sitemap.xml and extract product page URLs."""
        try:
            self.session.headers["User-Agent"] = "Mozilla/5.0 (compatible; DentalPrecios/1.0)"
            response = self.session.get(self.SITEMAP_URL, timeout=30)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[{self.name}] Failed to fetch sitemap: {e}")
            return []

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            logger.error(f"[{self.name}] Failed to parse sitemap XML: {e}")
            return []

        # Handle XML namespaces - sitemap uses default namespace
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []

        # Try with namespace first, then without
        loc_elements = root.findall(".//sm:loc", ns)
        if not loc_elements:
            loc_elements = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if not loc_elements:
            # Fallback: try without namespace
            loc_elements = root.findall(".//loc")

        for loc in loc_elements:
            url = loc.text.strip() if loc.text else ""
            if not url:
                continue

            # Skip non-product pages
            if self._is_product_url(url):
                urls.append(url)

        return urls

    def _is_product_url(self, url: str) -> bool:
        """Check if a sitemap URL is an individual product page."""
        # Must end with .aspx
        if not url.lower().endswith(".aspx"):
            return False

        # Skip known non-product patterns
        for pattern in SKIP_PATTERNS:
            if pattern in url:
                return False

        # Product URLs typically contain "Odonto-" prefix or match
        # the pattern /[product-slug]-[ID].aspx
        # They should NOT contain query parameters (those are navigation pages)
        if "?" in url:
            return False

        # Must have a numeric ID before .aspx (e.g., "...-1939.aspx")
        if re.search(r'-\d+\.aspx$', url, re.IGNORECASE):
            return True

        return False

    def _scrape_product_page(self, url: str) -> Optional[Dict]:
        """Scrape a single product page using JSON-LD + HTML fallback."""
        soup = self.fetch(url)
        if not soup:
            return None

        # Check if it's an error/404 page
        error_text = soup.find(string=re.compile(r"caries digital|no encontr", re.IGNORECASE))
        if error_text:
            return None

        # --- Strategy 1: JSON-LD structured data (most reliable) ---
        product_data = self._parse_json_ld(soup)

        # --- Strategy 2: HTML fallback ---
        if not product_data:
            product_data = self._parse_html(soup, url)

        if not product_data:
            return None

        # Ensure we have at minimum a name and price
        if not product_data.get("name") or not product_data.get("price"):
            return None

        # Set the product URL
        product_data["product_url"] = url

        # --- Enrich with HTML-only fields (brand, original_price, image) ---
        self._enrich_from_html(soup, product_data)

        return product_data

    def _parse_json_ld(self, soup) -> Optional[Dict]:
        """Extract product data from JSON-LD schema.org markup."""
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            # Handle both single object and list
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") != "Product":
                    continue

                name = item.get("name", "").strip()
                if not name:
                    continue

                offers = item.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}

                price = self._parse_clp(str(offers.get("price", "0")))
                if price <= 0:
                    continue

                availability = offers.get("availability", "")
                in_stock = "InStock" in availability if availability else True

                image_url = item.get("image", "")
                # Fix relative image URLs and skip empty/root-only URLs
                if image_url and image_url != "https://www.odontoimport.cl/":
                    if not image_url.startswith("http"):
                        image_url = f"{self.base_url}/{image_url.lstrip('/')}"
                else:
                    image_url = ""

                return {
                    "name": name,
                    "price": price,
                    "in_stock": in_stock,
                    "image_url": image_url if image_url else None,
                }

        return None

    def _parse_html(self, soup, url: str) -> Optional[Dict]:
        """Fallback: parse product data from HTML elements."""
        # Product name from h1
        h1 = soup.find("h1")
        if not h1:
            return None
        name = h1.get_text(strip=True)
        if not name:
            return None

        # Find price in page text - look for CLP patterns like $XX.XXX
        price = 0
        price_matches = re.findall(r'\$[\d.,]+', soup.get_text())
        if price_matches:
            # The last price is typically the sale/current price
            # Try to get the lowest non-zero price
            prices = [self._parse_clp(p) for p in price_matches]
            prices = [p for p in prices if p > 0]
            if prices:
                price = min(prices)

        if price <= 0:
            return None

        return {
            "name": name,
            "price": price,
            "in_stock": True,
        }

    def _enrich_from_html(self, soup, product_data: Dict):
        """Add brand, original_price, and image_url from HTML if missing."""
        page_text = soup.get_text()

        # --- Brand ---
        brand_match = re.search(r'Marca:\s*(.+?)(?:\n|$)', page_text)
        if brand_match:
            brand = brand_match.group(1).strip()
            if brand:
                product_data["brand"] = brand

        # --- Original price (struck-through / higher price) ---
        # Look for multiple prices on the page; the higher one is the original
        price_matches = re.findall(r'\$([\d.]+)', page_text)
        if len(price_matches) >= 2:
            parsed_prices = []
            for p in price_matches:
                val = self._parse_clp(p)
                if val > 0:
                    parsed_prices.append(val)
            # Deduplicate
            unique_prices = sorted(set(parsed_prices), reverse=True)
            if len(unique_prices) >= 2:
                highest = unique_prices[0]
                current = product_data["price"]
                if highest > current:
                    product_data["original_price"] = highest

        # --- Image URL (if not set from JSON-LD) ---
        if not product_data.get("image_url"):
            img = soup.find("img", src=re.compile(r'docs/productos/'))
            if img:
                src = img.get("src", "")
                if src and not src.startswith("http"):
                    src = f"{self.base_url}/{src.lstrip('/')}"
                product_data["image_url"] = src

    def _parse_clp(self, text: str) -> int:
        """Parse CLP price string like '$29.970' or '29970' to integer."""
        if not text:
            return 0
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def test(self) -> bool:
        """Test that the scraper can reach the site and fetch the sitemap."""
        try:
            response = self.session.get(self.SITEMAP_URL, timeout=15)
            if response.status_code != 200:
                print(f"ERROR: Sitemap returned status {response.status_code}")
                return False

            # Verify we can parse URLs from it
            urls = self._get_product_urls()
            print(f"OK: Found {len(urls)} product URLs in sitemap")

            if not urls:
                print("ERROR: No product URLs found in sitemap")
                return False

            # Test fetching one product page
            soup = self.fetch(urls[0])
            if not soup:
                print(f"ERROR: Could not fetch product page {urls[0]}")
                return False

            product = self._scrape_product_page(urls[0])
            if product:
                print(f"OK: Sample product: {product['name']} - ${product['price']:,}")
                return True
            else:
                print("WARNING: Could fetch page but failed to parse product")
                return False

        except Exception as e:
            print(f"ERROR: {e}")
            return False
