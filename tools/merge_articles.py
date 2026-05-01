"""Merge seo_inventory.json + content_bodies.json by article ID.

Output: tools/articles_full.json

Usage:
    python tools/merge_articles.py
    python tools/merge_articles.py --inventory tools/seo_inventory.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Merge SEO inventory with article bodies.")
    parser.add_argument("--inventory", default="tools/seo_inventory.json")
    parser.add_argument("--bodies", default="tools/content_bodies.json")
    parser.add_argument("--output", default="tools/articles_full.json")
    args = parser.parse_args()

    inv_path = Path(args.inventory)
    bodies_path = Path(args.bodies)
    out_path = Path(args.output)

    if not inv_path.exists():
        print(f"ERROR: {inv_path} not found.", file=sys.stderr)
        sys.exit(1)
    if not bodies_path.exists():
        print(f"ERROR: {bodies_path} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading inventory ({inv_path})…")
    with inv_path.open(encoding="utf-8") as f:
        inventory: list[dict] = json.load(f)

    print(f"Loading bodies ({bodies_path})…")
    with bodies_path.open(encoding="utf-8") as f:
        bodies_raw: list[dict] = json.load(f)

    # Build body map: id → {introtext, fulltext}
    body_map: dict[int, dict] = {}
    for b in bodies_raw:
        try:
            aid = int(b.get("id") or b.get("article_id", 0))
        except (ValueError, TypeError):
            continue
        body_map[aid] = b

    print(f"Inventory: {len(inventory)}, Bodies: {len(body_map)}")

    merged = []
    matched = 0
    missing = 0

    for art in inventory:
        try:
            aid = int(art.get("id", 0))
        except (ValueError, TypeError):
            merged.append(art)
            missing += 1
            continue

        body_entry = body_map.get(aid)
        if body_entry:
            intro = (body_entry.get("introtext") or "").strip()
            full = (body_entry.get("fulltext") or "").strip()
            # Combine: intro + <hr> + full (якщо обидва є)
            if intro and full:
                body = intro + "\n" + full
            else:
                body = intro or full
            art["body"] = body
            matched += 1
        else:
            art.setdefault("body", "")
            missing += 1

        merged.append(art)

    print(f"Matched: {matched}, Missing bodies: {missing}")

    print(f"Writing to {out_path}…")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False)

    print(f"Done! {len(merged)} articles written to {out_path}")


if __name__ == "__main__":
    main()
