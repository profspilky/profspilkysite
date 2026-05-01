"""
Verify every URL from seo_inventory.json against a running Django dev server.

Usage:
    python tools/verify_urls.py                          # default: http://localhost:8001
    python tools/verify_urls.py --base http://localhost:8000
    python tools/verify_urls.py --types article          # only article URLs
    python tools/verify_urls.py --limit 200 --workers 10
    python tools/verify_urls.py --report report.json     # save full report

Output:
  - Summary counts: OK / 404 / Other
  - List of failing URLs with expected vs actual status
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path(__file__).parent
INVENTORY = BASE_DIR / "seo_inventory.json"


def check_url(base: str, url_path: str) -> tuple[str, int]:
    full = base.rstrip("/") + url_path
    try:
        req = urllib.request.Request(full, method="GET")
        req.add_header("User-Agent", "SEO-Verifier/1.0")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return url_path, resp.status
    except urllib.error.HTTPError as e:
        return url_path, e.code
    except Exception:
        return url_path, -1


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Joomla→Django URL coverage")
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--inventory", default=str(INVENTORY))
    parser.add_argument("--types", nargs="*", help="Filter URL types: article category menu")
    parser.add_argument("--limit", type=int, default=0, help="Max URLs to check (0=all)")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--report", help="Save full JSON report to this file")
    args = parser.parse_args()

    inv_path = Path(args.inventory)
    if not inv_path.exists():
        print(f"Inventory not found: {inv_path}")
        sys.exit(1)

    inventory = json.loads(inv_path.read_text(encoding="utf-8"))
    urls = inventory.get("all_urls", [])

    if args.types:
        urls = [u for u in urls if u.get("type") in args.types]

    if args.limit:
        urls = urls[: args.limit]

    total = len(urls)
    print(f"Checking {total} URLs against {args.base} ({args.workers} workers)…")

    results: list[dict] = []
    ok = not_found = other = error = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(check_url, args.base, u["url"]): u for u in urls
        }
        done = 0
        for future in as_completed(futures):
            url_info = futures[future]
            path, status = future.result()
            done += 1

            result = {
                "url": path,
                "status": status,
                "type": url_info.get("type"),
                "title": url_info.get("title", ""),
            }
            results.append(result)

            if status == 200:
                ok += 1
            elif status == 404:
                not_found += 1
            elif status == -1:
                error += 1
            else:
                other += 1

            if done % 500 == 0:
                print(f"  {done}/{total}…")

    failing = [r for r in results if r["status"] != 200]
    failing.sort(key=lambda r: r["url"])

    print()
    print("=" * 60)
    print(f"Total:    {total}")
    print(f"  ✓ 200:  {ok}  ({ok/total*100:.1f}%)")
    print(f"  ✗ 404:  {not_found}")
    print(f"  ? other:{other}")
    print(f"  ! err:  {error}")
    print()

    if failing:
        print(f"Failing URLs ({len(failing)}):")
        for r in failing[:50]:
            print(f"  [{r['status']}]  {r['url']}")
        if len(failing) > 50:
            print(f"  … and {len(failing)-50} more")

    if args.report:
        report_path = Path(args.report)
        report_path.write_text(
            json.dumps({"summary": {"total": total, "ok": ok, "not_found": not_found,
                                    "other": other, "error": error},
                        "failing": failing, "all": results},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nReport saved → {report_path}")


if __name__ == "__main__":
    main()
