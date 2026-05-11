"""
Example supplier scraper template.
Copy this file and adapt for each new dental supplier.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseScraper


class ExampleScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            supplier_name="Example Dental Store",
            base_url="https://example-dental.cl",
        )

    def test(self) -> bool:
        """Verify the site structure hasn't changed."""
        soup = self.fetch(self.base_url + "/productos")
        if not soup:
            return False
        return bool(soup.select(".product-card"))

    def scrape(self) -> list[dict]:
        """Scrape all products from this supplier."""
        products = []
        page = 1

        while True:
            soup = self.fetch(f"{self.base_url}/productos?page={page}")
            if not soup:
                break

            cards = soup.select(".product-card")
            if not cards:
                break

            for card in cards:
                name = card.select_one(".product-name")
                price = card.select_one(".product-price")
                link = card.select_one("a")

                if name and price and link:
                    price_text = price.get_text(strip=True)
                    price_int = int(price_text.replace("$", "").replace(".", "").strip())

                    products.append({
                        "name": name.get_text(strip=True),
                        "price": price_int,
                        "url": self.base_url + link["href"],
                        "in_stock": True,
                    })

            page += 1

        return products
