"""
Scraper for Dentosmed (dentosmed.cl)
Platform: WooCommerce + Porto theme
Products: Dental supplies, instruments, equipment
Prices: CLP, publicly visible

History:
  2026-05-08 — site rebuilt: permalink base went from /categoria/{slug-2}/ to
  /categoria-producto/{slug}/ (standard WP), and theme switched from Flatsome
  to Porto. Container is now <div class="product product-col"> (porto-tb-item)
  rather than <div class="product-small">. Pagination URLs and standard WC
  price selectors are unchanged.
"""
from __future__ import annotations

from suppliers.woo_generic import WooGenericScraper


class DentosmedScraper(WooGenericScraper):
    name = "Dentosmed"
    base_url = "https://www.dentosmed.cl"
    website_url = "https://www.dentosmed.cl"

    category_url_pattern = "/categoria-producto/{category}/"

    categories = [
        "1-dental/22-cirugia",
        "1-dental/23-desechables",
        "1-dental/24-esterilizacion",
        "1-dental/33-periodoncia",
        "1-dental/25-radiologia",
        "1-dental/26-ortodoncia",
        "1-dental/21-restauracion",
        "1-dental/27-endodoncia",
        "1-dental/15-implantes",
        "1-dental/34-laboratorio",
        "1-dental/32-impresion",
        "1-dental/37-instrumental",
        "1-dental/28-rotatorios",
        "1-dental/6-accesorios",
        "1-dental/31-higiene-bucal",
        "1-dental/29-aire-y-succion",
        "1-dental/41-ortopedia",
    ]

    pagination_style = "path"

    # Porto theme container. CSS class selectors are exact-token, so
    # ".product-block__price" is not matched by ".product".
    product_selector = "div.product.product-col"
