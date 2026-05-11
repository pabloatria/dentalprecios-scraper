"""
Scraper for Techdent (techdent.cl)
Platform: WooCommerce + Astra + Elementor
Products: Equipment, instruments, consumables
Prices: CLP, publicly visible
"""
from __future__ import annotations

from typing import List, Dict
from suppliers.woo_generic import WooGenericScraper


class TechdentScraper(WooGenericScraper):
    name = "Techdent"
    base_url = "https://techdent.cl"
    website_url = "https://techdent.cl"
    use_playwright_stealth = True

    categories = [
        "accesorios-para-clinica-dental",
        "insumos-dentales/desechables-para-dentistas",
        "insumos-dentales/insumos-instrumental-dental",
        "insumos-dentales/fresas-dentales",
        "equipamiento-dental/equipamiento-cirugia-dental",
        "equipamiento-dental/compresores-y-bombas-de-succion",
        "equipamiento-dental/esterilizacion-y-desinfeccion",
        "equipamiento-dental/imagen-digital",
        "equipamiento-dental/mobiliario-clinico-dental",
        "equipamiento-dental/sillones-dentales",
        "equipamiento-dental/repuestos-y-mantenimiento-de-equipos-dentales",
        "laboratorio/equipos-para-laboratorio",
    ]

    category_url_pattern = "/product-category/{category}/"
    product_selector = "li.product"
    link_selector = "a.woocommerce-LoopProduct-link"
