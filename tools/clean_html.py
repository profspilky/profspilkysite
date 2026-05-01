"""Clean HTML bodies extracted from Joomla.

Usage:
    python tools/clean_html.py --dry-run --sample 50
    python tools/clean_html.py --input tools/articles_full.json --output tools/articles_clean.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import bleach
from bs4 import BeautifulSoup

# ── Allowed HTML tags and attributes ──────────────────────────────────────────
ALLOWED_TAGS = [
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "strong", "b", "em", "i", "u", "s", "strike",
    "blockquote", "pre", "code",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "figure", "figcaption",
    "div", "span",
]

ALLOWED_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "table": ["summary"],
    "th": ["scope", "colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
    "div": ["class"],
    "span": ["class"],
    "p": ["class"],
    "h1": ["id"], "h2": ["id"], "h3": ["id"], "h4": ["id"],
}

# ── Joomla-specific patterns to strip ─────────────────────────────────────────
JOOMLA_PATTERNS: list[re.Pattern] = [
    re.compile(r"\{loadposition\s+[\w\s]+\}", re.IGNORECASE),
    re.compile(r"\{loadmodule\s+[\w\s,]+\}", re.IGNORECASE),
    re.compile(r"\{module\s+\d+\}", re.IGNORECASE),
    re.compile(r"\{K2Splitter\}", re.IGNORECASE),
    re.compile(r"\{jcomments\s*[\w]*\}", re.IGNORECASE),
    re.compile(r"\{source\}", re.IGNORECASE),
    re.compile(r"\{\/source\}", re.IGNORECASE),
    re.compile(r"<!--\s*pagebreak\s*-->", re.IGNORECASE),
]

# Inline styles worth stripping entirely
INLINE_STYLE_RE = re.compile(r'\s*style="[^"]*"', re.IGNORECASE)
FONT_SIZE_JUNK_RE = re.compile(r'<font[^>]*>(.*?)</font>', re.IGNORECASE | re.DOTALL)
CENTER_TAG_RE = re.compile(r'<center>(.*?)</center>', re.IGNORECASE | re.DOTALL)


def strip_joomla_tokens(html: str) -> str:
    for pattern in JOOMLA_PATTERNS:
        html = pattern.sub("", html)
    return html


def replace_legacy_tags(html: str) -> str:
    # <center>...</center> → <div class="text-center">...</div>
    html = CENTER_TAG_RE.sub(r'<div class="text-center">\1</div>', html)
    # <font ...>...</font> → remove tag, keep content
    html = FONT_SIZE_JUNK_RE.sub(r'\1', html)
    return html


def strip_inline_styles(html: str) -> str:
    return INLINE_STYLE_RE.sub("", html)


def fix_image_paths(html: str, image_map: dict[str, str]) -> str:
    """Replace Joomla-relative image paths with Cloudinary URLs."""
    if not image_map:
        return html

    def replace_src(m: re.Match) -> str:
        src = m.group(1)
        # Нормалізуємо шлях
        src_clean = src.lstrip("/")
        mapped = image_map.get(src_clean) or image_map.get(src)
        if mapped:
            return f'src="{mapped}"'
        return m.group(0)

    return re.sub(r'src="([^"]+)"', replace_src, html)


def clean(html: str, image_map: dict[str, str] | None = None) -> str:
    if not html or not html.strip():
        return ""

    # 1. Видалити Joomla-токени
    html = strip_joomla_tokens(html)

    # 2. Замінити застарілі теги
    html = replace_legacy_tags(html)

    # 3. Прибрати inline-стилі
    html = strip_inline_styles(html)

    # 4. Виправити шляхи зображень (якщо є маппінг)
    if image_map:
        html = fix_image_paths(html, image_map)

    # 5. BeautifulSoup нормалізує HTML
    soup = BeautifulSoup(html, "lxml")
    html = str(soup.body) if soup.body else str(soup)
    # Прибираємо тег <body> якщо BeautifulSoup додав
    html = re.sub(r'^<body>(.*)</body>$', r'\1', html, flags=re.DOTALL).strip()

    # 6. bleach strip заборонених тегів та атрибутів
    html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
        strip_comments=True,
    )

    return html.strip()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Clean Joomla HTML bodies.")
    parser.add_argument("--input", default="tools/articles_full.json")
    parser.add_argument("--output", default="tools/articles_clean.json")
    parser.add_argument("--image-map", default="tools/image_map.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sample", type=int, default=0, help="Process only N articles (0 = all)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    image_map_path = Path(args.image_map)

    if not input_path.exists():
        print(f"ERROR: {input_path} not found. Run merge_articles.py first.", file=sys.stderr)
        sys.exit(1)

    image_map: dict[str, str] = {}
    if image_map_path.exists():
        image_map = json.loads(image_map_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(image_map)} image mappings.")

    print(f"Loading {input_path}…")
    articles: list[dict] = json.loads(input_path.read_text(encoding="utf-8"))

    if args.sample:
        articles = articles[:args.sample]
        print(f"Processing sample of {len(articles)} articles.")

    cleaned = []
    skipped = 0
    token_hits = 0

    for i, art in enumerate(articles):
        body = art.get("body") or ""
        if not body:
            skipped += 1
            cleaned.append(art)
            continue

        # Count Joomla tokens for statistics
        for pat in JOOMLA_PATTERNS:
            if pat.search(body):
                token_hits += 1
                break

        art["body"] = clean(body, image_map)
        cleaned.append(art)

        if (i + 1) % 1000 == 0:
            print(f"  Processed {i + 1}/{len(articles)}…")

    print(f"\nResults: {len(cleaned)} processed, {skipped} skipped (no body), {token_hits} had Joomla tokens.")

    if not args.dry_run:
        output_path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=None), encoding="utf-8")
        print(f"Saved to {output_path}")
    else:
        print("DRY RUN — output not written.")
        if cleaned:
            print("\n── Sample (first cleaned article) ──")
            print(cleaned[0].get("body", "")[:500])


if __name__ == "__main__":
    main()
