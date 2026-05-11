#!/usr/bin/env python3
"""
Weekly robots.txt monitor.
Checks all scraped supplier sites for changes to their robots.txt policies.
Alerts if a site adds scraping restrictions we should be concerned about.

Usage:
    python robots_monitor.py              # Check all sites
    python robots_monitor.py --diff-only  # Only show sites with changes
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# All supplier sites we actively scrape
SCRAPED_SITES = [
    "https://spdental.shop",
    "https://nexodental.cl",
    "https://eksadental.cl",
    "https://dentobal.cl",
    "https://gexachile.cl",
    "https://3dental.cl",
    "https://afchilespa.cl",
    "https://parejalecaros.cl",
    "https://www.bamssupplies.com",
    "https://dentsolutions.cl",
    "https://www.superdental.cl",
    "https://expressdent.cl",
    "https://siromax.cl",
    "https://www.dispolab.cl",
    "https://dentalmacaya.cl",
    "https://dipromed.cl",
    "https://naturabel.cl",
    "https://www.flamamed.cl",
    "https://dentalamerica.cl",
    "https://dentalmaxspa.cl",
    "https://orthomedical.cl",
    "https://www.tiendadentinet.com",
    "https://techdent.cl",
    "https://www.orbisdental.cl",
    "https://torregal.cl",
    "https://clandent.cl",
    "https://www.mayordent.cl",
    "https://denteeth.cl",
    "https://www.dentosmed.cl",
    "https://gipfel.cl",
    "https://www.biomateriales.cl",
    "https://www.biotechchile.cl",
    "https://depodental.cl",
]

# Patterns that indicate concern for our scraping activity
# Note: Shopify standard robots.txt blocks /products/ (search) and /collections/
# with trailing slash but NOT /products/handle — those are false positives.
CONCERN_PATTERNS = [
    r"disallow:\s*/\s*$",                    # Blanket block
    r"disallow:\s*/shop\s*$",                # Blocks shop root
    r"disallow:\s*/tienda",                  # Blocks store (Spanish)
    r"scraping.*prohib|prohib.*scraping",    # Explicit scraping ban
    r"automated.*access.*prohib",            # Automated access ban
    r"crawl-delay:\s*(\d+)",                 # Rate limiting (flag if > 30)
    r"ai-input\s*=\s*no",                    # Blocks AI input usage
]

SNAPSHOT_FILE = Path(__file__).parent / ".robots_snapshots.json"


def fetch_robots(url: str) -> dict:
    """Fetch robots.txt for a site and return parsed info."""
    robots_url = f"{url.rstrip('/')}/robots.txt"
    try:
        resp = requests.get(robots_url, timeout=15, headers={
            "User-Agent": "DentalPrecios-RobotsMonitor/1.0"
        })
        if resp.status_code == 200:
            text = resp.text
            # Check if it returned HTML instead of robots.txt
            if text.strip().startswith("<!") or text.strip().startswith("<html"):
                return {"status": "no_robots", "content": "", "hash": ""}
            content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            return {"status": "ok", "content": text, "hash": content_hash}
        elif resp.status_code == 404:
            return {"status": "no_robots", "content": "", "hash": ""}
        else:
            return {"status": f"http_{resp.status_code}", "content": "", "hash": ""}
    except requests.Timeout:
        return {"status": "timeout", "content": "", "hash": ""}
    except requests.RequestException as e:
        return {"status": f"error: {str(e)[:80]}", "content": "", "hash": ""}


def check_concerns(content: str) -> list[str]:
    """Check robots.txt content for patterns that concern our scraping."""
    concerns = []
    content_lower = content.lower()

    for pattern in CONCERN_PATTERNS:
        matches = re.findall(pattern, content_lower, re.MULTILINE)
        if matches:
            if "crawl-delay" in pattern:
                for delay in matches:
                    if int(delay) > 30:
                        concerns.append(f"High crawl-delay: {delay}s")
            elif "disallow" in pattern and "disallow:\\s*/\\s*$" in pattern:
                # Check if blanket disallow applies to all user-agents (not just specific ones)
                # Simple heuristic: if "User-agent: *" precedes "Disallow: /"
                lines = content_lower.split("\n")
                in_star_block = False
                for line in lines:
                    line = line.strip()
                    if line.startswith("user-agent:"):
                        in_star_block = "*" in line
                    elif in_star_block and re.match(r"disallow:\s*/\s*$", line):
                        concerns.append("Blanket Disallow: / for all user-agents")
                        break
            else:
                concerns.append(f"Pattern match: {pattern}")

    return concerns


def load_snapshots() -> dict:
    """Load previous snapshots from disk."""
    if SNAPSHOT_FILE.exists():
        with open(SNAPSHOT_FILE) as f:
            return json.load(f)
    return {}


def save_snapshots(snapshots: dict):
    """Save snapshots to disk."""
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(snapshots, f, indent=2)


def run_check(diff_only: bool = False) -> dict:
    """Run the full check and return a report."""
    snapshots = load_snapshots()
    new_snapshots = {}
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changed": [],
        "new_concerns": [],
        "existing_concerns": [],
        "errors": [],
        "ok": [],
    }

    for site in SCRAPED_SITES:
        result = fetch_robots(site)
        old = snapshots.get(site, {})
        old_hash = old.get("hash", "")

        new_snapshots[site] = {
            "hash": result["hash"],
            "status": result["status"],
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "concerns": [],
        }

        if result["status"] not in ("ok", "no_robots"):
            report["errors"].append({"site": site, "status": result["status"]})
            new_snapshots[site]["concerns"] = old.get("concerns", [])
            continue

        # Check for concerns
        concerns = check_concerns(result["content"])
        new_snapshots[site]["concerns"] = concerns

        # Detect changes
        changed = old_hash != "" and old_hash != result["hash"]

        if changed:
            report["changed"].append({
                "site": site,
                "old_hash": old_hash,
                "new_hash": result["hash"],
                "concerns": concerns,
            })

        if concerns and not old.get("concerns"):
            report["new_concerns"].append({"site": site, "concerns": concerns})
        elif concerns:
            report["existing_concerns"].append({"site": site, "concerns": concerns})
        elif not diff_only:
            report["ok"].append(site)

    save_snapshots(new_snapshots)
    return report


def format_report(report: dict) -> str:
    """Format report as readable text."""
    lines = []
    lines.append(f"=== Robots.txt Monitor Report ===")
    lines.append(f"Timestamp: {report['timestamp']}")
    lines.append(f"Sites checked: {len(SCRAPED_SITES)}")
    lines.append("")

    if report["changed"]:
        lines.append("!! CHANGED robots.txt (review needed):")
        for item in report["changed"]:
            lines.append(f"  - {item['site']}")
            if item["concerns"]:
                for c in item["concerns"]:
                    lines.append(f"    CONCERN: {c}")
        lines.append("")

    if report["new_concerns"]:
        lines.append("!! NEW CONCERNS detected:")
        for item in report["new_concerns"]:
            lines.append(f"  - {item['site']}")
            for c in item["concerns"]:
                lines.append(f"    {c}")
        lines.append("")

    if report["existing_concerns"]:
        lines.append("Known existing concerns (unchanged):")
        for item in report["existing_concerns"]:
            lines.append(f"  - {item['site']}: {', '.join(item['concerns'])}")
        lines.append("")

    if report["errors"]:
        lines.append("Errors (could not fetch):")
        for item in report["errors"]:
            lines.append(f"  - {item['site']}: {item['status']}")
        lines.append("")

    if report["ok"]:
        lines.append(f"OK ({len(report['ok'])} sites with no concerns)")
        lines.append("")

    has_alerts = bool(report["changed"] or report["new_concerns"])
    if has_alerts:
        lines.append("ACTION REQUIRED: Review the changes above.")
    else:
        lines.append("All clear - no new changes or concerns detected.")

    return "\n".join(lines)


if __name__ == "__main__":
    diff_only = "--diff-only" in sys.argv
    report = run_check(diff_only)
    print(format_report(report))

    # Exit with code 1 if there are alerts (useful for CI/cron)
    if report["changed"] or report["new_concerns"]:
        sys.exit(1)
