"""
Scraper for Dentobal (dentobal.cl)
Platform: Shopify — uses JSON API
Cloudflare protected — uses cloudscraper
Products: Dental supplies, instruments, materials
Prices: CLP, publicly visible
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict
from suppliers.shopify_generic import ShopifyGenericScraper

logger = logging.getLogger(__name__)


class DentobalScraper(ShopifyGenericScraper):
    name = "Dentobal"
    base_url = "https://dentobal.cl"
    website_url = "https://dentobal.cl"
    use_cloudscraper = True
    use_playwright_stealth = True
