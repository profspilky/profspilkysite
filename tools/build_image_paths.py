"""
Build tools/image_paths.txt — list of all .webp files under media/joomla_images/images/.

The relative paths (relative to media/joomla_images/) are stored one per line.
Used by upload_images_cloudinary.py.

Usage:
    python tools/build_image_paths.py
    python tools/build_image_paths.py --limit 1000   # лише перші 1000 шляхів (тест)
    python tools/build_image_paths.py --media-dir media/joomla_images
"""
from __future__ import annotations

import argparse
from pathlib import Path

BASE = Path(__file__).parent.parent
MEDIA_DIR = BASE / "media" / "joomla_images"
OUTPUT = Path(__file__).parent / "image_paths.txt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max paths to write (0 = all). Use 1000 for a small test list.",
    )
    args = parser.parse_args()

    media = Path(args.media_dir)
    out = Path(args.output)

    if not media.exists():
        print(f"ERROR: {media} not found.")
        return

    paths: list[str] = []
    for f in sorted(media.rglob("*.webp")):
        rel = f.relative_to(media)
        paths.append(str(rel))

    # Also include .jpg/.png that weren't converted
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.gif"):
        for f in sorted(media.rglob(ext)):
            rel = f.relative_to(media)
            key = str(rel)
            # Skip if webp version exists (already covered)
            webp_path = f.with_suffix(".webp")
            if not webp_path.exists():
                paths.append(key)

    paths = sorted(set(paths))
    if args.limit and args.limit > 0:
        paths = paths[: args.limit]
        print(f"Limit: first {len(paths)} paths (--limit {args.limit})")
    print(f"Found {len(paths)} image files → {out}")


if __name__ == "__main__":
    main()
