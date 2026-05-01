"""Replace Joomla-relative image paths in article bodies with Cloudinary URLs.

Requires: tools/image_map.json (built by upload_images_cloudinary.py)

Usage:
    python tools/replace_image_paths.py --input tools/articles_full.json
    python tools/replace_image_paths.py --dry-run --sample 20
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


SRC_PATTERN = re.compile(r'src="(/images/[^"]+|images/[^"]+)"', re.IGNORECASE)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="tools/articles_clean.json")
    parser.add_argument("--output", default="tools/articles_clean.json")
    parser.add_argument("--image-map", default="tools/image_map.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    image_map_path = Path(args.image_map)

    if not input_path.exists():
        print(f"ERROR: {input_path} not found.", file=sys.stderr)
        sys.exit(1)

    image_map: dict[str, str] = {}
    if image_map_path.exists():
        image_map = json.loads(image_map_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(image_map)} mappings.")
    else:
        print(f"WARNING: {image_map_path} not found. No replacements will happen.")

    articles: list[dict] = json.loads(input_path.read_text(encoding="utf-8"))
    if args.sample:
        articles = articles[: args.sample]

    replaced_count = 0
    total_replacements = 0

    for art in articles:
        body = art.get("body", "")
        if not body:
            continue

        def replace_src(m: re.Match) -> str:
            nonlocal total_replacements
            src = m.group(1).lstrip("/")
            mapped = image_map.get(src) or image_map.get(f"/{src}")
            if mapped:
                total_replacements += 1
                return f'src="{mapped}"'
            return m.group(0)

        new_body = SRC_PATTERN.sub(replace_src, body)
        if new_body != body:
            art["body"] = new_body
            replaced_count += 1

    print(f"Articles with replacements: {replaced_count}, Total src replacements: {total_replacements}")

    if not args.dry_run:
        output_path.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
        print(f"Saved to {output_path}")
    else:
        print("DRY RUN — not saved.")


if __name__ == "__main__":
    main()
