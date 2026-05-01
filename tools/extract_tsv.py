"""
Parse tools/fpsu_full_dump.sql in ONE pass and produce:

  tools/cats.tsv              – categories  (compatible with parse_joomla_dump.py)
  tools/articles.tsv          – article metadata
  tools/menu.tsv              – menu items
  tools/content_bodies.json   – article intro+full text
  tools/tags.json             – tags
  tools/gallery.json          – JoomGallery images
  tools/gallery_cats.json     – JoomGallery categories

Usage:
    python3 tools/extract_tsv.py
    python3 tools/extract_tsv.py --sql tools/fpsu_full_dump.sql
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
DEFAULT_SQL = BASE / "fpsu_full_dump.sql"


# ── Low-level MySQL SQL value parser (reused from parse_bodies.py) ──────────

def _parse_string(text: str, pos: int) -> tuple[str, int]:
    buf: list[str] = []
    pos += 1
    while pos < len(text):
        ch = text[pos]
        if ch == "\\":
            pos += 1
            if pos >= len(text):
                break
            esc = text[pos]
            buf.append(
                "\n" if esc == "n"
                else "\r" if esc == "r"
                else "\t" if esc == "t"
                else "'" if esc == "'"
                else '"' if esc == '"'
                else "\\" if esc == "\\"
                else "\0" if esc == "0"
                else esc
            )
        elif ch == "'":
            pos += 1
            break
        else:
            buf.append(ch)
        pos += 1
    return "".join(buf), pos


def _parse_value(text: str, pos: int) -> tuple[str | None, int]:
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    if pos >= len(text):
        return "", pos
    if text[pos: pos + 4] == "NULL":
        return None, pos + 4
    if text[pos] == "'":
        return _parse_string(text, pos)
    start = pos
    while pos < len(text) and text[pos] not in ",)":
        pos += 1
    return text[start:pos].strip(), pos


def _skip_to_row_end(text: str, pos: int) -> int:
    in_string = False
    depth = 0
    while pos < len(text):
        ch = text[pos]
        if in_string:
            if ch == "\\":
                pos += 2
                continue
            if ch == "'":
                in_string = False
        else:
            if ch == "'":
                in_string = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    return pos + 1
                depth -= 1
        pos += 1
    return pos


def _parse_row(text: str, start: int, wanted: frozenset[int], max_col: int) -> tuple[dict | None, int]:
    pos = start + 1
    col = 0
    values: dict[int, str | None] = {}

    while pos < len(text) and col <= max_col:
        while pos < len(text) and text[pos] in " \t":
            pos += 1
        if pos >= len(text):
            break
        if text[pos] == ")":
            pos += 1
            break

        val, pos = _parse_value(text, pos)
        if col in wanted:
            values[col] = val
        col += 1

        while pos < len(text) and text[pos] in " \t":
            pos += 1
        if pos < len(text):
            if text[pos] == ",":
                pos += 1
            elif text[pos] == ")":
                pos += 1
                break

    if col <= max_col and pos < len(text) and (not text[pos - 1:pos] == ")"):
        pos = _skip_to_row_end(text, pos)

    return values if values else None, pos


def _parse_insert(line: str, wanted: frozenset[int], max_col: int) -> list[dict]:
    marker = " VALUES "
    idx = line.find(marker)
    if idx == -1:
        return []
    pos = idx + len(marker)
    rows: list[dict] = []
    while pos < len(line):
        ch = line[pos]
        if ch == "(":
            row, pos = _parse_row(line, pos, wanted, max_col)
            if row is not None:
                rows.append(row)
        elif ch in (",", " ", "\t"):
            pos += 1
        elif ch == ";":
            break
        else:
            pos += 1
    return rows


# ── Table specs ──────────────────────────────────────────────────────────────

# zeki2_content columns used
_CONTENT_WANTED = frozenset({0, 2, 3, 4, 5, 6, 7, 15, 17, 22, 23})
_CONTENT_MAX = 23

# zeki2_categories columns: id(0), path(6), title(8), alias(9), metadesc(17), metakey(18)
_CATS_WANTED = frozenset({0, 6, 8, 9, 17, 18})
_CATS_MAX = 18

# zeki2_menu columns: id(0), title(2), alias(3), path(5), link(6), type(7), parent_id(9)
_MENU_WANTED = frozenset({0, 2, 3, 5, 6, 7, 9})
_MENU_MAX = 9

# zeki2_tags columns: id(0), path(5), title(6), alias(7)
_TAGS_WANTED = frozenset({0, 5, 6, 7})
_TAGS_MAX = 7

# zeki2_joomgallery: id(0),catid(2),imgtitle(3),alias(4),imgtext(6),imgdate(7),
#                    published(13),imgfilename(16),imgthumbname(17),metakey(24),metadesc(25)
_GALLERY_WANTED = frozenset({0, 2, 3, 4, 6, 7, 13, 16, 17, 24, 25})
_GALLERY_MAX = 25

# zeki2_joomgallery_catg: cid(0),name(2),alias(3),parent_id(4),description(8),
#                         published(10),catpath(17),metakey(19),metadesc(20)
_GCATG_WANTED = frozenset({0, 2, 3, 4, 8, 10, 17, 19, 20})
_GCATG_MAX = 20


# ── INSERT line prefixes → (wanted, max_col, table_key) ─────────────────────

_TABLE_MAP = {
    "INSERT INTO `zeki2_content` VALUES": ("content", _CONTENT_WANTED, _CONTENT_MAX),
    "INSERT INTO `zeki2_categories` VALUES": ("cats", _CATS_WANTED, _CATS_MAX),
    "INSERT INTO `zeki2_menu` VALUES": ("menu", _MENU_WANTED, _MENU_MAX),
    "INSERT INTO `zeki2_tags` VALUES": ("tags", _TAGS_WANTED, _TAGS_MAX),
    "INSERT INTO `zeki2_joomgallery` VALUES": ("gallery", _GALLERY_WANTED, _GALLERY_MAX),
    "INSERT INTO `zeki2_joomgallery_catg` VALUES": ("gcatg", _GCATG_WANTED, _GCATG_MAX),
}


# ── Output builders ──────────────────────────────────────────────────────────

def _build_cats_tsv(rows: list[dict]) -> str:
    lines: list[str] = []
    for r in rows:
        lines.append("\t".join([
            r.get(0) or "",   # id
            r.get(9) or "",   # alias
            r.get(8) or "",   # title
            (r.get(6) or "").strip("/"),  # path
            r.get(17) or "",  # metadesc
            r.get(18) or "",  # metakey
        ]))
    return "\n".join(lines)


def _build_articles_tsv(rows: list[dict]) -> str:
    lines: list[str] = []
    for r in rows:
        lines.append("\t".join([
            r.get(0) or "",   # id
            r.get(3) or "",   # alias
            r.get(7) or "",   # catid
            r.get(2) or "",   # title
            r.get(23) or "",  # metadesc
            r.get(22) or "",  # metakey
            r.get(17) or "",  # images JSON
            r.get(15) or "",  # publish_up
        ]))
    return "\n".join(lines)


def _build_menu_tsv(rows: list[dict]) -> str:
    lines: list[str] = []
    for r in rows:
        lines.append("\t".join([
            r.get(0) or "",   # id
            r.get(2) or "",   # title
            r.get(3) or "",   # alias
            r.get(5) or "",   # path
            r.get(6) or "",   # link
            r.get(7) or "",   # type
            r.get(9) or "",   # parent_id
        ]))
    return "\n".join(lines)


def _build_bodies_json(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        try:
            row_id = int(r.get(0) or 0)
        except ValueError:
            continue
        if not row_id:
            continue
        out.append({
            "id": row_id,
            "title": r.get(2) or "",
            "alias": r.get(3) or "",
            "introtext": r.get(4) or "",
            "fulltext": r.get(5) or "",
            "state": int(r.get(6) or 0),
            "catid": int(r.get(7) or 0),
            "publish_up": r.get(15) or "",
        })
    return out


def _build_tags_json(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": r.get(0) or "",
            "path": r.get(5) or "",
            "title": r.get(6) or "",
            "alias": r.get(7) or "",
        }
        for r in rows
    ]


def _build_gallery_json(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": r.get(0) or "",
            "catid": r.get(2) or "",
            "title": r.get(3) or "",
            "alias": r.get(4) or "",
            "description": r.get(6) or "",
            "date": r.get(7) or "",
            "published": r.get(13) or "0",
            "filename": r.get(16) or "",
            "thumb": r.get(17) or "",
            "metakey": r.get(24) or "",
            "metadesc": r.get(25) or "",
        }
        for r in rows
    ]


def _build_gcatg_json(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": r.get(0) or "",
            "name": r.get(2) or "",
            "alias": r.get(3) or "",
            "parent_id": r.get(4) or "",
            "description": r.get(8) or "",
            "published": r.get(10) or "0",
            "catpath": r.get(17) or "",
            "metakey": r.get(19) or "",
            "metadesc": r.get(20) or "",
        }
        for r in rows
    ]


# ── Main ─────────────────────────────────────────────────────────────────────

def main(sql_path: Path) -> None:
    if not sql_path.exists():
        print(f"ERROR: {sql_path} not found", file=sys.stderr)
        sys.exit(1)

    buckets: dict[str, list[dict]] = {k: [] for k in ("content", "cats", "menu", "tags", "gallery", "gcatg")}
    insert_counts: dict[str, int] = {k: 0 for k in buckets}

    print(f"Parsing {sql_path}  ({sql_path.stat().st_size / 1_048_576:.0f} MB) …")

    with sql_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for prefix, (key, wanted, max_col) in _TABLE_MAP.items():
                if line.startswith(prefix):
                    rows = _parse_insert(line.rstrip("\n\r"), wanted, max_col)
                    buckets[key].extend(rows)
                    insert_counts[key] += 1
                    if insert_counts[key] % 50 == 0:
                        print(f"  {key}: {insert_counts[key]} INSERTs / {len(buckets[key])} rows …")
                    break

    print("\n=== Parsed rows ===")
    for k, rows in buckets.items():
        print(f"  {k:12s}: {len(rows):6d} rows ({insert_counts[k]} INSERTs)")

    # cats.tsv
    out = BASE / "cats.tsv"
    out.write_text(_build_cats_tsv(buckets["cats"]), encoding="utf-8")
    print(f"\nSaved: {out}")

    # articles.tsv
    out = BASE / "articles.tsv"
    out.write_text(_build_articles_tsv(buckets["content"]), encoding="utf-8")
    print(f"Saved: {out}")

    # menu.tsv
    out = BASE / "menu.tsv"
    out.write_text(_build_menu_tsv(buckets["menu"]), encoding="utf-8")
    print(f"Saved: {out}")

    # content_bodies.json
    out = BASE / "content_bodies.json"
    bodies = _build_bodies_json(buckets["content"])
    out.write_text(json.dumps(bodies, ensure_ascii=False, indent=2), encoding="utf-8")
    pub = sum(1 for b in bodies if b["state"] == 1)
    print(f"Saved: {out}  ({len(bodies)} articles, {pub} published)")

    # tags.json
    out = BASE / "tags.json"
    tags = _build_tags_json(buckets["tags"])
    out.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}  ({len(tags)} tags)")

    # gallery.json
    out = BASE / "gallery.json"
    gallery = _build_gallery_json(buckets["gallery"])
    out.write_text(json.dumps(gallery, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}  ({len(gallery)} images)")

    # gallery_cats.json
    out = BASE / "gallery_cats.json"
    gcatg = _build_gcatg_json(buckets["gcatg"])
    out.write_text(json.dumps(gcatg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}  ({len(gcatg)} gallery categories)")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract TSV/JSON from Joomla SQL dump")
    parser.add_argument("--sql", default=str(DEFAULT_SQL))
    args = parser.parse_args()
    main(Path(args.sql))
