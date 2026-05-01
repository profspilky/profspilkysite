"""
Stream-parse zeki2_content from fpsu_seo_dump.sql and write
tools/content_bodies.json with article body content.

Extracted columns (by position in INSERT VALUES rows):
  0  id          → "id"
  2  title       → "title"
  3  alias       → "alias"
  4  introtext   → "introtext"
  5  fulltext    → "fulltext"
  6  state       → "state"
  7  catid       → "catid"
  15 publish_up  → "publish_up"

Usage:
    python tools/parse_bodies.py
    python tools/parse_bodies.py --sql tools/fpsu_seo_dump.sql --out tools/content_bodies.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
DEFAULT_SQL = BASE / "fpsu_seo_dump.sql"
DEFAULT_OUT = BASE / "content_bodies.json"

TABLE = "zeki2_content"
# 0-based column indices we need; stop parsing after MAX_NEEDED_COL
_WANTED: frozenset[int] = frozenset({0, 2, 3, 4, 5, 6, 7, 15})
_MAX_NEEDED_COL: int = 15


# ── Low-level MySQL SQL tokeniser ─────────────────────────────────────────────

def _parse_string(text: str, pos: int) -> tuple[str, int]:
    """
    Parse a MySQL single-quoted string starting at `pos` (the opening quote).
    Handles all MySQL escape sequences.
    Returns (unescaped_value, position_after_closing_quote).
    """
    buf: list[str] = []
    pos += 1  # skip opening '
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
            pos += 1
        elif ch == "'":
            pos += 1  # skip closing '
            break
        else:
            buf.append(ch)
            pos += 1
    return "".join(buf), pos


def _parse_value(text: str, pos: int) -> tuple[str | None, int]:
    """
    Parse one SQL value (string, integer, float, or NULL) starting at `pos`.
    Skips leading whitespace.
    Returns (value_as_str_or_None, next_pos).
    """
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    if pos >= len(text):
        return "", pos
    if text[pos : pos + 4] == "NULL":
        return None, pos + 4
    if text[pos] == "'":
        return _parse_string(text, pos)
    # Integer / float / bare word
    start = pos
    while pos < len(text) and text[pos] not in ",)":
        pos += 1
    return text[start:pos].strip(), pos


def _skip_to_row_end(text: str, pos: int) -> int:
    """
    Fast-forward from `pos` (just after the last parsed column) to the position
    immediately after the closing ')' of the current VALUES row.
    Correctly handles strings and nested parentheses.
    """
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


def _parse_row(text: str, start: int) -> tuple[dict | None, int]:
    """
    Parse one VALUES row starting at `start` (the opening '(').
    Returns (row_dict_or_None, position_after_closing_paren).
    """
    pos = start + 1  # skip '('
    col = 0
    values: dict[int, str | None] = {}

    while pos < len(text) and col <= _MAX_NEEDED_COL:
        # Skip whitespace
        while pos < len(text) and text[pos] in " \t":
            pos += 1
        if pos >= len(text):
            break
        ch = text[pos]
        if ch == ")":
            pos += 1
            break

        # Parse the value at the current column
        val, pos = _parse_value(text, pos)
        if col in _WANTED:
            values[col] = val

        col += 1

        # After each value: expect ',' (next col) or ')' (row end)
        while pos < len(text) and text[pos] in " \t":
            pos += 1
        if pos < len(text):
            if text[pos] == ",":
                pos += 1  # advance to next column
            elif text[pos] == ")":
                pos += 1
                break

    # If we still have columns > MAX_NEEDED_COL, fast-forward to ')'
    if col <= _MAX_NEEDED_COL and pos < len(text) and text[pos] not in ")":
        pos = _skip_to_row_end(text, pos)
    elif pos < len(text) and text[pos - 1] != ")":
        pos = _skip_to_row_end(text, pos)

    if 0 not in values:
        return None, pos

    try:
        row_id = int(values[0]) if values[0] is not None else None
        if row_id is None:
            return None, pos
        return {
            "id": row_id,
            "title": values.get(2) or "",
            "alias": values.get(3) or "",
            "introtext": values.get(4) or "",
            "fulltext": values.get(5) or "",
            "state": int(values.get(6) or 0),
            "catid": int(values.get(7) or 0),
            "publish_up": str(values.get(15) or ""),
        }, pos
    except (TypeError, ValueError):
        return None, pos


def _parse_insert_line(line: str) -> list[dict]:
    """
    Parse all VALUES rows from a single INSERT INTO `table` VALUES (...),(...);
    line.
    """
    marker = " VALUES "
    idx = line.find(marker)
    if idx == -1:
        return []
    pos = idx + len(marker)

    rows: list[dict] = []
    while pos < len(line):
        ch = line[pos]
        if ch == "(":
            row, pos = _parse_row(line, pos)
            if row is not None:
                rows.append(row)
        elif ch in (",", " ", "\t"):
            pos += 1
        elif ch == ";":
            break
        else:
            pos += 1
    return rows


# ── Main ─────────────────────────────────────────────────────────────────────

def main(sql_path: Path, out_path: Path) -> None:
    if not sql_path.exists():
        print(f"ERROR: SQL dump not found: {sql_path}", file=sys.stderr)
        sys.exit(1)

    prefix = f"INSERT INTO `{TABLE}` VALUES "
    all_rows: list[dict] = []
    insert_count = 0
    line_num = 0

    print(f"Parsing {sql_path} …")
    with sql_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line_num += 1
            if not line.startswith(prefix):
                continue
            insert_count += 1
            rows = _parse_insert_line(line.rstrip("\n\r"))
            all_rows.extend(rows)
            if insert_count % 50 == 0:
                print(f"  INSERT #{insert_count} — {len(all_rows)} rows so far …")

    print(f"\nParsed {insert_count} INSERT statement(s), {len(all_rows)} total rows.")

    published = sum(1 for r in all_rows if r["state"] == 1)
    print(f"  Published (state=1): {published}")
    print(f"  Other states:        {len(all_rows) - published}")

    out_path.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved → {out_path}  ({out_path.stat().st_size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse zeki2_content bodies from SQL dump")
    parser.add_argument("--sql", default=str(DEFAULT_SQL), help="Path to .sql dump")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path")
    args = parser.parse_args()
    main(Path(args.sql), Path(args.out))
