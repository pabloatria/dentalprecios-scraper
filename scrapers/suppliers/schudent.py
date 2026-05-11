"""
Scraper for Schudent (schudent.cl)
Platform: Shopify (migrated from WooCommerce on/around 2026-04-10)
Products: SprintRay 3D printers, CAD/CAM blocks, resins, instruments
Prices: CLP (IVA included), publicly visible
Notable: Official SprintRay distributor in Chile, Aidite CAD blocks

History:
  Pre-2026-04-10 — WooCommerce HTML scrape of /tienda/. After migration the
  /tienda/ path 404s and product pages live under /products/{handle}. The
  public /products.json API returns the full catalog (~77 products), so we
  use ShopifyGenericScraper. Vendor field carries real brand names (Erkodent,
  SprintRay, Aidite, etc.) so vendor_is_brand stays True.
"""
from __future__ import annotations

from suppliers.shopify_generic import ShopifyGenericScraper


class SchudentScraper(ShopifyGenericScraper):
    name = "Schudent"
    base_url = "https://schudent.cl"
    website_url = "https://schudent.cl"
