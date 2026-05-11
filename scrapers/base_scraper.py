from __future__ import annotations

import os
import json as _json
import requests
import time
import random
import logging
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def _get_proxy() -> Optional[dict]:
    """Get proxy config from SCRAPER_PROXY env var if set.
    Supports HTTP/HTTPS/SOCKS5 proxies.
    Example: socks5://user:pass@host:port or http://host:port
    """
    proxy_url = os.environ.get("SCRAPER_PROXY")
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


class _PlaywrightResponse:
    """Minimal requests.Response-compatible wrapper around Playwright's APIResponse."""

    def __init__(self, status_code: int, body_text: str, url: str):
        self.status_code = status_code
        self.text = body_text
        self.content = body_text.encode("utf-8", errors="replace")
        self.url = url

    def json(self):
        return _json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Client Error for url: {self.url}"
            )


_PW_SINGLETON = None
_PW_BROWSER = None


def _get_shared_browser():
    """Lazy-initialize a single Playwright + Chromium for the whole process.

    Playwright's sync API uses an internal greenlet+asyncio loop that can only
    be started once per process. Calling sync_playwright().start() a second
    time raises "Sync API inside the asyncio loop." So we share one browser
    across every PlaywrightStealthSession and give each session its own
    BrowserContext (cheap, isolated cookies/storage).
    """
    global _PW_SINGLETON, _PW_BROWSER
    if _PW_BROWSER is not None:
        return _PW_BROWSER
    from playwright.sync_api import sync_playwright
    _PW_SINGLETON = sync_playwright().start()
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
    ]
    _PW_BROWSER = _PW_SINGLETON.chromium.launch(headless=True, args=launch_args)
    return _PW_BROWSER


class PlaywrightStealthSession:
    """requests.Session drop-in backed by Playwright+stealth for anti-bot sites.

    - Shares one headless Chromium across all sessions (Playwright sync API
      can only be started once per process)
    - Each session owns an isolated BrowserContext (own cookies, own UA)
    - First request to a host warms the context (triggers CF challenge,
      collects cf_clearance cookies) before hitting the target URL
    - Subsequent requests reuse the context so API/JSON calls inherit cookies
    """

    _warmed_hosts: set

    def __init__(self, name: str = "PW"):
        self._stealth = None
        self._stealth_sync = None
        try:
            from playwright_stealth import Stealth
            self._stealth = Stealth()
        except ImportError:
            pass
        try:
            from playwright_stealth import stealth_sync
            self._stealth_sync = stealth_sync
        except ImportError:
            pass

        self._name = name
        self._warmed_hosts = set()
        self.headers: Dict[str, str] = {}
        self.proxies = None

        self._browser = _get_shared_browser()
        self._context = self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="es-CL",
            timezone_id="America/Santiago",
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.5",
            },
        )
        # Apply stealth patches (varies by library version)
        if self._stealth is not None:
            try:
                self._stealth.apply_stealth_sync(self._context)
            except AttributeError:
                pass

        self._page = self._context.new_page()
        if self._stealth is None and self._stealth_sync is not None:
            try:
                self._stealth_sync(self._page)
            except Exception as e:
                logger.warning(f"[{self._name}] stealth_sync failed: {e}")

    def _has_cf_clearance(self, host: str) -> bool:
        try:
            for c in self._context.cookies():
                if c.get("name") == "cf_clearance" and host.endswith(c.get("domain", "").lstrip(".")):
                    return True
        except Exception:
            pass
        return False

    def _is_cf_challenge_page(self) -> bool:
        """Heuristic: CF interstitial has a recognizable title or body marker."""
        try:
            title = (self._page.title() or "").lower()
            if "just a moment" in title or "attention required" in title:
                return True
            # Fallback: body contains the CF challenge script marker
            html = self._page.content()[:4000].lower()
            return ("challenge-platform" in html or "cf-browser-verification" in html)
        except Exception:
            return False

    def _warm_host(self, url: str):
        """Visit homepage and linger until CF challenge clears + cf_clearance cookie is set.

        Tiers of stubborn:
        1. No CF: homepage loads fast, no challenge → done in ~3s
        2. Basic CF: interstitial auto-redirects within 5-10s → wait it out
        3. "Under attack" CF: needs extra reload or category-page visit → fallback
        """
        host = urlparse(url).netloc
        if not host or host in self._warmed_hosts:
            return
        try:
            self._page.goto(f"https://{host}/", wait_until="domcontentloaded", timeout=45000)
            # Poll up to 20s for cf_clearance cookie + challenge to clear
            deadline = time.time() + 20
            while time.time() < deadline:
                if self._has_cf_clearance(host) and not self._is_cf_challenge_page():
                    break
                self._page.wait_for_timeout(750)

            # If still on challenge page, try one reload — sometimes the token
            # only drops after a second request.
            if self._is_cf_challenge_page():
                logger.info(f"[{self._name}] CF challenge still visible on {host}, reloading")
                try:
                    self._page.reload(wait_until="domcontentloaded", timeout=30000)
                    self._page.wait_for_timeout(4000)
                except Exception:
                    pass

            got_cookie = self._has_cf_clearance(host)
            logger.info(
                f"[{self._name}] Warmed host {host} "
                f"(cf_clearance={'yes' if got_cookie else 'no'})"
            )
            self._warmed_hosts.add(host)
        except Exception as e:
            logger.warning(f"[{self._name}] Warm-up failed for {host}: {e}")

    def get(self, url: str, params: Optional[dict] = None, timeout: int = 30, **kwargs):
        if params:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urlencode(params)}"

        self._warm_host(url)

        # Decide between API request (JSON/XHR path) and full navigation.
        # Strip query string before checking .json so /products.json?limit=2 matches.
        path_only = url.split("?", 1)[0]
        is_api = (
            "/wp-json/" in url
            or path_only.endswith(".json")
            or "/api/" in url
        )
        try:
            if is_api:
                # Run the request FROM the already-authenticated page context via
                # window.fetch — Cloudflare treats this as a legitimate XHR from
                # the origin and inherits cf_clearance cookies. context.request.get()
                # bypasses the page and often gets 403'd on CF-protected APIs.
                fetch_js = """async (u) => {
                    try {
                        const r = await fetch(u, {
                            credentials: 'include',
                            headers: { 'Accept': 'application/json, text/plain, */*' },
                        });
                        const text = await r.text();
                        return { status: r.status, body: text };
                    } catch (e) {
                        return { status: 599, body: String(e) };
                    }
                }"""

                def _looks_like_challenge(status: int, body: str) -> bool:
                    if status in (202, 403, 503):
                        return True
                    if body and body.lstrip().lower().startswith("<!doctype html"):
                        return True
                    return False

                result = self._page.evaluate(fetch_js, url)
                status = int(result.get("status", 599))
                body = result.get("body", "")

                # If CF is serving a challenge on the API endpoint, re-warm
                # (reload page → wait → retry) up to twice.
                attempts = 0
                while _looks_like_challenge(status, body) and attempts < 2:
                    attempts += 1
                    host = urlparse(url).netloc
                    logger.info(
                        f"[{self._name}] API challenge (status={status}), re-warming {host} "
                        f"attempt {attempts}/2"
                    )
                    try:
                        self._page.reload(wait_until="domcontentloaded", timeout=30000)
                        self._page.wait_for_timeout(4000 + attempts * 2000)
                    except Exception:
                        pass
                    result = self._page.evaluate(fetch_js, url)
                    status = int(result.get("status", 599))
                    body = result.get("body", "")

                return _PlaywrightResponse(status, body, url)
            else:
                response = self._page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                # Some sites serve CF challenge first; a short extra wait lets the
                # real content render before we grab HTML.
                try:
                    self._page.wait_for_timeout(1500)
                except Exception:
                    pass
                status = response.status if response else 200
                body = self._page.content()
                return _PlaywrightResponse(status, body, url)
        except Exception as e:
            logger.error(f"[{self._name}] Playwright GET failed for {url}: {e}")
            return _PlaywrightResponse(599, "", url)

    def close(self):
        # Only close the per-session context — the browser + Playwright are
        # shared across all scrapers and torn down once at process exit
        # via shutdown_shared_browser().
        try:
            self._context.close()
        except Exception:
            pass


def shutdown_shared_browser():
    """Tear down the shared Playwright instance. Call once at process exit."""
    global _PW_SINGLETON, _PW_BROWSER
    if _PW_BROWSER is not None:
        try:
            _PW_BROWSER.close()
        except Exception:
            pass
        _PW_BROWSER = None
    if _PW_SINGLETON is not None:
        try:
            _PW_SINGLETON.stop()
        except Exception:
            pass
        _PW_SINGLETON = None


class BaseScraper:
    """Base class for all supplier scrapers."""

    name = "Base"
    base_url = ""
    website_url = ""
    use_cloudscraper = False  # Set True for Cloudflare-protected sites
    use_playwright_stealth = False  # Set True to route all requests through Playwright+stealth

    def __init__(self):
        proxy = _get_proxy()

        if self.use_playwright_stealth:
            self.session = PlaywrightStealthSession(name=self.name)
        elif self.use_cloudscraper:
            import cloudscraper
            self.session = cloudscraper.create_scraper()
        else:
            self.session = requests.Session()

        # requests/cloudscraper sessions support .headers.update; PW session has a stub
        if hasattr(self.session, "headers") and hasattr(self.session.headers, "update"):
            self.session.headers.update({
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.5",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                # Only advertise encodings requests can decode natively. Advertising "br"
                # without the brotli package installed made Shopify's CDN serve brotli-
                # encoded /products.json that requests returned as raw bytes, breaking
                # .json() across every Shopify scraper on 2026-03-20.
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })

        if proxy and not self.use_playwright_stealth:
            self.session.proxies = proxy
            logger.info(f"[{self.name}] Using proxy")

    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return parsed HTML."""
        try:
            time.sleep(random.uniform(1.5, 4.0))
            # Rotate user agent per request (requests/cloudscraper only — PW context is fixed)
            if not self.use_playwright_stealth and hasattr(self.session, "headers"):
                self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error(f"[{self.name}] Error fetching {url}: {e}")
            return None

    def close(self):
        """Clean up resources (Playwright browser, etc.)."""
        if isinstance(self.session, PlaywrightStealthSession):
            self.session.close()

    def scrape(self) -> List[Dict]:
        """Override in subclass. Returns list of product dicts."""
        raise NotImplementedError

    def test(self) -> bool:
        """Override in subclass. Returns True if scraper selectors still work."""
        raise NotImplementedError
