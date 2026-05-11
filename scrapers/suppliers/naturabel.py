"""
Scraper for Naturabel (naturabel.cl)
Platform: Shopify — uses public /products.json API
Products: Aesthetic medicine (Innoaesthetics, KSurgery Opera fillers, Meline depigmentation)
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class NaturabelScraper(ShopifyGenericScraper):
    name = "Naturabel"
    base_url = "https://naturabel.cl"
    website_url = "https://naturabel.cl"
