"""
Daily scraper health check.

Queries Supabase for last scraped_at per supplier and flags any that haven't
returned fresh data in >48h. Writes a markdown report to stdout and exits 1
if any supplier is stale (so the GH Actions workflow opens an issue).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta

from supabase import create_client

STALE_HOURS = 48
URGENT_DAYS = 5

url = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
sb = create_client(url, key)

now = datetime.now(timezone.utc)

# Use server-side GROUP BY via Postgres function — avoids PostgREST 1000-row cap
# and N+1 timeout issues.  Function: get_supplier_freshness() → (supplier_id, supplier_name, last_scraped)
freshness = sb.rpc("get_supplier_freshness", {}).execute().data or []
if not freshness:
    print("ERROR: get_supplier_freshness() returned no rows — check DB function exists")
    sys.exit(2)

rows = []
for r in freshness:
    last_str = r.get("last_scraped")
    if last_str:
        last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
        age_h = (now - last_dt).total_seconds() / 3600
    else:
        last_dt = None
        age_h = float("inf")
    rows.append({"name": r["supplier_name"], "last": last_dt, "age_h": age_h})

rows.sort(key=lambda r: r["age_h"], reverse=True)

stale = [r for r in rows if r["age_h"] > STALE_HOURS]
urgent = [r for r in rows if r["age_h"] > URGENT_DAYS * 24]

print(f"# Scraper health — {now.strftime('%Y-%m-%d %H:%M UTC')}\n")
print(f"- Total suppliers: {len(rows)}")
print(f"- Fresh (≤{STALE_HOURS}h): {len(rows) - len(stale)}")
print(f"- Stale (>{STALE_HOURS}h): {len(stale)}")
print(f"- Urgent (>{URGENT_DAYS}d): {len(urgent)}\n")

if stale:
    print(f"## Stale suppliers (>{STALE_HOURS}h)\n")
    print("| Supplier | Last scrape | Age |")
    print("|---|---|---|")
    for r in stale:
        last_str = r["last"].strftime("%Y-%m-%d %H:%M") if r["last"] else "NEVER"
        if r["age_h"] == float("inf"):
            age_str = "never"
        elif r["age_h"] > 24:
            age_str = f"{r['age_h']/24:.1f}d"
        else:
            age_str = f"{r['age_h']:.1f}h"
        flag = " 🚨" if r in urgent else ""
        print(f"| {r['name']}{flag} | {last_str} | {age_str} |")
    print()

if urgent:
    print(f"## URGENT — down >{URGENT_DAYS} days\n")
    for r in urgent:
        print(f"- **{r['name']}** — last seen {r['last'].strftime('%Y-%m-%d') if r['last'] else 'NEVER'}")
    print()

print("## All suppliers (sorted by staleness)\n")
print("| Supplier | Last scrape | Age |")
print("|---|---|---|")
for r in rows:
    last_str = r["last"].strftime("%Y-%m-%d %H:%M") if r["last"] else "NEVER"
    if r["age_h"] == float("inf"):
        age_str = "never"
    elif r["age_h"] > 24:
        age_str = f"{r['age_h']/24:.1f}d"
    else:
        age_str = f"{r['age_h']:.1f}h"
    print(f"| {r['name']} | {last_str} | {age_str} |")

sys.exit(1 if stale else 0)
