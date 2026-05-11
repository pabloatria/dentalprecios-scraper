"""
Scraper for Dispolab (dispolab.cl)
Platform: Shopify — uses public /products.json API
Products: Facial aesthetic supplies (Fillmed fillers, Juvelook, cannulas, threads, mesotherapy)
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class DispolabScraper(ShopifyGenericScraper):
    name = "Dispolab"
    base_url = "https://www.dispolab.cl"
    website_url = "https://www.dispolab.cl"
