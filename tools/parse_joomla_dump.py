"""
Build seo_inventory.json from tab-separated exports of Joomla MySQL tables.

Input files (tools/):
  cats.tsv     – zeki2_categories (id, alias, title, path, metadesc, metakey)
  articles.tsv – zeki2_content    (id, alias, catid, title, metadesc, metakey,
                                   images_json, publish_date)
  menu.tsv     – zeki2_menu       (id, title, alias, path, link, type, parent_id)

Output:
  tools/seo_inventory.json

Usage:
    python tools/parse_joomla_dump.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
CATS_TSV = BASE / "cats.tsv"
ARTICLES_TSV = BASE / "articles.tsv"
MENU_TSV = BASE / "menu.tsv"
OUT = BASE / "seo_inventory.json"

_IMG_FIELDS = ("image_intro", "image_fulltext")


def _read_tsv(path: Path, num_cols: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) < num_cols:
            continue
        # Merge overflow columns into the last expected column
        if len(parts) > num_cols:
            parts = parts[: num_cols - 1] + ["\t".join(parts[num_cols - 1 :])]
        rows.append(parts)
    return rows


def _extract_images(images_json: str) -> list[str]:
    if not images_json or images_json in ("NULL", ""):
        return []
    try:
        data = json.loads(images_json)
    except json.JSONDecodeError:
        return []
    paths = []
    for field in _IMG_FIELDS:
        val = data.get(field, "")
        if val and val.strip():
            paths.append(val.strip())
    return paths


def main() -> None:
    for p in (CATS_TSV, ARTICLES_TSV, MENU_TSV):
        if not p.exists():
            print(f"Missing: {p}")
            sys.exit(1)

    # ── categories ────────────────────────────────────────────────────────────
    cats: dict[str, dict] = {}
    for row in _read_tsv(CATS_TSV, 6):
        cid, alias, title, path, metadesc, metakey = row
        cats[cid] = {
            "id": cid,
            "alias": alias,
            "title": title,
            "path": path.strip("/"),
            "metadesc": metadesc,
            "metakey": metakey,
        }
    print(f"Categories: {len(cats)}")

    # ── articles ──────────────────────────────────────────────────────────────
    all_image_paths: set[str] = set()
    all_urls: list[dict] = []
    articles_out: list[dict] = []

    for row in _read_tsv(ARTICLES_TSV, 8):
        jid, alias, catid, title, metadesc, metakey, images_json, publish_date = row
        if jid in ("NULL", ""):
            continue

        cat = cats.get(catid, {})
        cat_path = cat.get("path", "").strip("/")
        images = _extract_images(images_json)
        for img in images:
            all_image_paths.add(img)

        if cat_path:
            url_path = f"/{cat_path}/{jid}-{alias}.html"
        else:
            url_path = f"/{jid}-{alias}.html"

        art = {
            "joomla_id": jid,
            "alias": alias,
            "catid": catid,
            "cat_alias": cat.get("alias", ""),
            "cat_path": cat_path,
            "title": title,
            "metadesc": metadesc,
            "metakey": metakey,
            "images": images,
            "publish_date": publish_date,
            "url_path": url_path,
        }
        articles_out.append(art)
        all_urls.append({
            "url": url_path,
            "title": title,
            "metadesc": metadesc,
            "type": "article",
            "joomla_id": jid,
        })

    print(f"Articles:   {len(articles_out)}")

    # Category listing URLs
    for cat in cats.values():
        if cat["path"]:
            all_urls.append({
                "url": f"/{cat['path']}/",
                "title": cat["title"],
                "metadesc": cat["metadesc"],
                "type": "category",
            })

    # ── menu items ────────────────────────────────────────────────────────────
    menu_out: list[dict] = []
    for row in _read_tsv(MENU_TSV, 7):
        mid, title, alias, path, link, mtype, parent_id = row
        item = {
            "id": mid,
            "title": title,
            "alias": alias,
            "path": path,
            "link": link,
            "type": mtype,
            "parent_id": parent_id,
        }
        menu_out.append(item)
        if path and path not in ("NULL", ""):
            all_urls.append({
                "url": f"/{path}",
                "title": title,
                "metadesc": "",
                "type": "menu",
            })

    print(f"Menu items: {len(menu_out)}")
    print(f"Total URLs: {len(all_urls)}")
    print(f"Images:     {len(all_image_paths)}")

    inventory = {
        "categories": list(cats.values()),
        "articles": articles_out,
        "menu_items": menu_out,
        "all_urls": all_urls,
        "image_paths": sorted(all_image_paths),
    }

    OUT.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved → {OUT}")


if __name__ == "__main__":
    main()
