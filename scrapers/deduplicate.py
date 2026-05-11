"""
Product deduplication script.

Finds duplicate products across suppliers and merges them:
1. Moves all prices from alias products to the canonical product
2. Deletes alias products
3. Updates canonical product name to the shortest/cleanest version

Usage:
    # Dry run - generate CSV for review:
    python3 deduplicate.py

    # Apply merges after review:
    python3 deduplicate.py --apply
"""
from __future__ import annotations

import os
import sys
import csv
import logging
import argparse
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from matchers import (
    normalize_name,
    tokenize,
    jaccard_similarity,
    pick_canonical_name,
    extract_brand,
    shared_brand,
    are_same_product,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

OUTPUT_CSV = "dedup_review.csv"


def fetch_all_products(supabase) -> list[dict]:
    """Fetch all products from the database."""
    all_products = []
    page_size = 1000
    offset = 0

    while True:
        result = supabase.table("products") \
            .select("id, name, brand, category_id, image_url") \
            .range(offset, offset + page_size - 1) \
            .execute()

        if not result.data:
            break

        all_products.extend(result.data)

        if len(result.data) < page_size:
            break

        offset += page_size

    return all_products


def find_duplicate_groups(products: list[dict]) -> list[list[dict]]:
    """Find groups of duplicate products using greedy canonical clustering.

    Strategy (avoids transitive closure problems of Union-Find):
    1. Pre-tokenize all products
    2. Build an inverted index for fast candidate lookup
    3. Sort products by name length (shortest first = better canonical candidates)
    4. For each product, check if it matches a canonical of an existing group
    5. If yes, add to that group. If no, start a new group with this product.

    This ensures every member of a group matches the group's canonical,
    preventing chain-of-similarity issues.
    """
    n = len(products)
    logger.info(f"Finding duplicates among {n} products...")

    # Pre-tokenize
    tokens_list = [tokenize(p["name"]) for p in products]

    # Build inverted index for fast lookup
    token_index = defaultdict(set)
    for i, tokens in enumerate(tokens_list):
        for token in tokens:
            token_index[token].add(i)

    # Sort indices by name length (shorter names first = better canonicals)
    sorted_indices = sorted(range(n), key=lambda i: len(products[i]["name"]))

    # Greedy canonical-based clustering
    # Each group is (canonical_idx, [member_indices])
    groups = []  # list of (canonical_idx, [all indices including canonical])
    assigned = set()

    for i in sorted_indices:
        if i in assigned or not tokens_list[i]:
            continue

        # This product becomes a canonical. Find all matching unassigned products.
        group = [i]
        assigned.add(i)

        # Find candidates that share at least 2 tokens with this canonical
        candidate_counts = defaultdict(int)
        for token in tokens_list[i]:
            for j in token_index[token]:
                if j != i and j not in assigned:
                    candidate_counts[j] += 1

        for j, shared_count in candidate_counts.items():
            if shared_count < 2:
                continue
            if j in assigned:
                continue

            # Must match the canonical (not just any group member)
            if are_same_product(products[i]["name"], products[j]["name"]):
                group.append(j)
                assigned.add(j)

        if len(group) > 1:
            groups.append(group)

    # Convert to product dicts
    duplicate_groups = [[products[i] for i in g] for g in groups]
    total_aliases = sum(len(g) - 1 for g in duplicate_groups)
    logger.info(f"Found {len(duplicate_groups)} duplicate groups ({total_aliases} aliases)")

    return duplicate_groups


def write_review_csv(groups: list[list[dict]], filename: str):
    """Write duplicate groups to CSV for review."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "group_id", "action", "product_id", "current_name",
            "canonical_name", "brand", "category_id"
        ])

        for group_idx, group in enumerate(groups, 1):
            names = [p["name"] for p in group]
            canonical = pick_canonical_name(names)

            for product in group:
                action = "KEEP" if product["name"] == canonical else "MERGE"
                writer.writerow([
                    group_idx,
                    action,
                    product["id"],
                    product["name"],
                    canonical,
                    product.get("brand", ""),
                    product.get("category_id", ""),
                ])

    logger.info(f"Review CSV written to {filename}")


def apply_merges(supabase, groups: list[list[dict]]):
    """Apply the merges: move prices to canonical, delete aliases."""
    total_merged = 0
    total_deleted = 0

    for group_idx, group in enumerate(groups, 1):
        names = [p["name"] for p in group]
        canonical_name = pick_canonical_name(names)

        # Find the canonical product (the one we keep)
        canonical = next(p for p in group if p["name"] == canonical_name)
        aliases = [p for p in group if p["id"] != canonical["id"]]

        if not aliases:
            continue

        canonical_id = canonical["id"]
        alias_ids = [a["id"] for a in aliases]

        logger.info(
            f"Group {group_idx}: Keeping '{canonical_name}' ({canonical_id}), "
            f"merging {len(aliases)} aliases"
        )

        # Step 1: Move all prices from aliases to canonical
        for alias_id in alias_ids:
            try:
                # Check if canonical already has a price from this supplier
                # to avoid duplicate (product_id, supplier_id) pairs
                alias_prices = supabase.table("prices") \
                    .select("id, supplier_id") \
                    .eq("product_id", alias_id) \
                    .execute()

                canonical_prices = supabase.table("prices") \
                    .select("supplier_id") \
                    .eq("product_id", canonical_id) \
                    .execute()

                canonical_supplier_ids = {
                    p["supplier_id"] for p in (canonical_prices.data or [])
                }

                for price_row in (alias_prices.data or []):
                    if price_row["supplier_id"] in canonical_supplier_ids:
                        # Supplier already has a price for canonical - delete alias price
                        supabase.table("prices") \
                            .delete() \
                            .eq("id", price_row["id"]) \
                            .execute()
                    else:
                        # Move price to canonical product
                        supabase.table("prices") \
                            .update({"product_id": canonical_id}) \
                            .eq("id", price_row["id"]) \
                            .execute()

                total_merged += len(alias_prices.data or [])
            except Exception as e:
                logger.error(f"Failed to move prices for {alias_id}: {e}")
                continue

        # Step 2: Delete alias products
        for alias_id in alias_ids:
            try:
                # Double-check no prices remain
                remaining = supabase.table("prices") \
                    .select("id", count="exact") \
                    .eq("product_id", alias_id) \
                    .execute()

                if remaining.count and remaining.count > 0:
                    logger.warning(
                        f"Alias {alias_id} still has {remaining.count} prices, skipping delete"
                    )
                    continue

                supabase.table("products") \
                    .delete() \
                    .eq("id", alias_id) \
                    .execute()
                total_deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete alias product {alias_id}: {e}")

        # Step 3: Update canonical product name and fill missing fields
        updates = {"name": canonical_name}

        # Pick best brand from the group
        if not canonical.get("brand"):
            for p in group:
                if p.get("brand"):
                    updates["brand"] = p["brand"]
                    break

        # Pick best image from the group
        if not canonical.get("image_url"):
            for p in group:
                if p.get("image_url"):
                    updates["image_url"] = p["image_url"]
                    break

        # Pick best category from the group
        if not canonical.get("category_id"):
            for p in group:
                if p.get("category_id"):
                    updates["category_id"] = p["category_id"]
                    break

        try:
            supabase.table("products") \
                .update(updates) \
                .eq("id", canonical_id) \
                .execute()
        except Exception as e:
            logger.error(f"Failed to update canonical product {canonical_id}: {e}")

    logger.info(f"Merge complete: {total_merged} prices moved, {total_deleted} products deleted")


def main():
    parser = argparse.ArgumentParser(description="Deduplicate products")
    parser.add_argument("--apply", action="store_true",
                        help="Apply merges (default: dry run with CSV output)")
    args = parser.parse_args()

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Fetch all products
    products = fetch_all_products(supabase)
    logger.info(f"Fetched {len(products)} products")

    # Find duplicate groups
    groups = find_duplicate_groups(products)

    if not groups:
        logger.info("No duplicates found!")
        return

    # Print summary
    total_aliases = sum(len(g) - 1 for g in groups)
    print(f"\n{'='*60}")
    print(f"Found {len(groups)} duplicate groups ({total_aliases} products to merge)")
    print(f"{'='*60}\n")

    for i, group in enumerate(groups[:20], 1):  # Show first 20 groups
        names = [p["name"] for p in group]
        canonical = pick_canonical_name(names)
        print(f"Group {i}: '{canonical}'")
        for p in group:
            marker = " ✓ KEEP" if p["name"] == canonical else " ✗ MERGE"
            print(f"  {marker}  {p['name']}")
        print()

    if len(groups) > 20:
        print(f"... and {len(groups) - 20} more groups\n")

    # Write review CSV
    write_review_csv(groups, OUTPUT_CSV)

    if args.apply:
        logger.info("Applying merges...")
        apply_merges(supabase, groups)
    else:
        print(f"Dry run complete. Review {OUTPUT_CSV} then run with --apply")


if __name__ == "__main__":
    main()
