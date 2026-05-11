"""
Scraper for Dental Laval (dental-laval.cl)
Platform: Shopify
Products: Equipment, instruments, Zeiss microscopes/loupes, W&H, EMS, Septodont
Prices: CLP, publicly visible
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class DentalLavalScraper(ShopifyGenericScraper):
    name = "Dental Laval"
    base_url = "https://www.dental-laval.cl"
    website_url = "https://www.dental-laval.cl"
    vendor_is_brand = True  # Vendor field has real brands (Zeiss, W&H, Septodont, etc.)
    use_cloudscraper = True  # Cloudflare protected

    def __init__(self):
        super().__init__()
        # Cloudflare sends brotli/gzip; force identity to avoid decoding issues
        self.session.headers.update({"Accept-Encoding": "identity"})
