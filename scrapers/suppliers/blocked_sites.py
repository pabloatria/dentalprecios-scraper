"""
Placeholder scrapers for sites that return 403 (Cloudflare/bot protection).
These sites need browser automation (Playwright) to bypass protection.
For now they log a warning and return empty results.

Blocked sites:
- superdental.cl (WooCommerce + Cloudflare)
- mayordent.cl (Cloudflare)
- dentobal.cl (Cloudflare)
- siromax.cl (Cloudflare)

Non-functional sites:
- dental-laval.cl (site down - default cPanel page)
- schulzdental.cl (DNS resolution failure)

Custom platforms (require deeper investigation):
- odontoimport.cl (ASP.NET - no public prices visible)
"""
from __future__ import annotations

import logging
from typing import List, Dict
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BlockedSiteScraper(BaseScraper):
    """Placeholder for sites blocked by Cloudflare/bot protection."""

    name = "Blocked"
    base_url = ""
    website_url = ""
    block_reason = "403 Cloudflare"

    def scrape(self) -> List[Dict]:
        logger.warning(
            f"[{self.name}] Scraper skipped - {self.block_reason}. "
            f"Needs Playwright browser automation."
        )
        return []

    def test(self) -> bool:
        logger.warning(f"[{self.name}] Site blocked ({self.block_reason})")
        return False


class SuperDentalBlockedScraper(BlockedSiteScraper):
    name = "SuperDental"
    base_url = "https://www.superdental.cl"
    website_url = "https://www.superdental.cl"
    block_reason = "403 Cloudflare protection"


class MayordentBlockedScraper(BlockedSiteScraper):
    name = "MayorDent"
    base_url = "https://mayordent.cl"
    website_url = "https://mayordent.cl"
    block_reason = "403 Cloudflare protection"


class DentobalBlockedScraper(BlockedSiteScraper):
    name = "Dentobal"
    base_url = "https://dentobal.cl"
    website_url = "https://dentobal.cl"
    block_reason = "403 Cloudflare protection"


class SiromaxBlockedScraper(BlockedSiteScraper):
    name = "Siromax"
    base_url = "https://siromax.cl"
    website_url = "https://siromax.cl"
    block_reason = "403 Cloudflare protection"
