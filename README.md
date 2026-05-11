# dentalprecios-scraper

Daily price scraper for [dentalprecios.cl](https://www.dentalprecios.cl). Pulls public catalog data from Chilean dental supply distributors, normalizes SKUs, and writes prices to Supabase. Companion to the (private) main application repository.

## What this repo is

The data-collection layer for DentalPrecios. It does three things on a schedule:

1. **Daily price scrape** (`scrape.yml` + `scrapers/main.py`) — fetches public product pages from ~70 Chilean dental distributors and writes prices to Supabase.
2. **Scraper health check** (`scraper-health.yml` + `scrapers/health_check.py`) — alerts when the daily scrape didn't run or produced suspicious output.
3. **Robots.txt monitor** (`robots-monitor.yml` + `scrapers/robots_monitor.py`) — watches for changes to suppliers' `robots.txt` files so we know if a supplier's crawling policy has shifted.

All sources are public supplier websites. We do not log in to any system. We respect `robots.txt`, use polite request pacing, identify ourselves with a custom User-Agent that names the project, and do not scrape any personal information or pricing tied to specific customer accounts.

## What this repo is not

This repo contains only the data-collection layer. It does **not** contain:

- The DentalPrecios web application (Next.js)
- The mobile app
- Business logic, pricing strategy, or commercial documents
- Dentist or clinic accounts
- Any personal data of any kind

The web application is in a separate private repository.

## Architecture

```
┌──────────────────────────────────┐
│ ~70 Chilean dental distributors  │
│ (public catalog pages)           │
└────────────────┬─────────────────┘
                 │ HTTP / Playwright
                 ▼
┌──────────────────────────────────┐
│ GitHub Actions runner (this repo)│
│ scrapers/main.py orchestrates    │
│ scrapers/suppliers/*.py per site │
└────────────────┬─────────────────┘
                 │ Supabase service-role key
                 ▼
┌──────────────────────────────────┐
│ Supabase Postgres (sa-east-1)    │
│ • products                       │
│ • prices                         │
│ • suppliers                      │
└────────────────┬─────────────────┘
                 │ ISR cache invalidation
                 ▼
┌──────────────────────────────────┐
│ dentalprecios.cl (Vercel)        │
└──────────────────────────────────┘
```

## Adding a new supplier scraper

1. Create `scrapers/suppliers/<supplier_name>.py` following the pattern of an existing one.
2. Implement the `scrape()` function returning a list of `Product` instances.
3. Register the scraper in `scrapers/main.py`.
4. Test locally against the supplier's public site.
5. Open a PR.

Each supplier scraper is a self-contained module so a malformed scraper for one supplier never breaks the others.

## Running locally

```bash
cd scrapers
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Required environment variables (place in `scrapers/.env`, not committed):

```
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
ANTHROPIC_API_KEY=<for AI categorization features>
```

Then:

```bash
python main.py
```

## Schedule (production)

Workflows currently run in **cutover mode** (`workflow_dispatch` only, no schedule) while the migration from the previous repository is verified. The `schedule:` blocks in each workflow file are commented out with instructions for re-enabling.

Once we confirm the workflow runs cleanly here, the daily schedule will be re-enabled and the workflows in the previous repository will be permanently disabled.

## Privacy and ethical-scraping commitments

- We scrape only publicly accessible pages.
- We do not collect personal data of any kind (no patient records, no dentist accounts, no contact information beyond what suppliers publish as business contact info on their own sites).
- We respect `robots.txt` and use polite request pacing.
- We identify ourselves with a custom User-Agent that names the project and links to the website.
- If a supplier requests that we stop indexing their catalog, we honor the request without delay.

## License

MIT. See `LICENSE`.

## Inquiries

pablo@dentalprecios.cl
