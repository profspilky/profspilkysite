"""
Convert all images in media/joomla_images/ to WebP and delete originals.

- JPG/JPEG  → WebP quality=85 (lossy)
- PNG        → WebP quality=85 (keeps transparency via RGBA)
- GIF        → WebP quality=85 (first frame only; animated not supported on site)

Usage:
    python3 tools/convert_to_webp.py
    python3 tools/convert_to_webp.py --quality 90
    python3 tools/convert_to_webp.py --dry-run
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError

MEDIA_DIR = Path(__file__).parent.parent / "media" / "joomla_images"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif"}


def convert_one(args: tuple[Path, int, bool]) -> tuple[str, str]:
    """Returns (status, path_str). status: 'ok' | 'skip' | 'error'"""
    src, quality, dry_run = args

    if src.suffix.lower() == ".webp":
        return "skip", str(src)

    dst = src.with_suffix(".webp")

    if dst.exists():
        if not dry_run:
            src.unlink()
        return "skip", str(src)

    if dry_run:
        return "ok", str(src)

    try:
        with Image.open(src) as img:
            # Ensure mode is compatible with WebP
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            img.save(dst, "WEBP", quality=quality, method=4)

        src.unlink()
        return "ok", str(src)

    except UnidentifiedImageError:
        return "error", f"not an image: {src}"
    except Exception as exc:
        return "error", f"{src}: {exc}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = [
        p for p in MEDIA_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]

    total = len(files)
    print(f"Found {total} images to convert (quality={args.quality}, workers={args.workers})")
    if args.dry_run:
        print("DRY RUN — no changes will be made")

    tasks = [(f, args.quality, args.dry_run) for f in files]

    ok = skip = errors = 0
    done = 0

    with mp.Pool(args.workers) as pool:
        for status, info in pool.imap_unordered(convert_one, tasks, chunksize=50):
            done += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                errors += 1
                print(f"  ERROR: {info}", file=sys.stderr)

            if done % 2000 == 0 or done == total:
                pct = done / total * 100
                print(f"  {done}/{total} ({pct:.0f}%)  converted={ok}  skipped={skip}  errors={errors}")

    print(f"\nDone: {ok} converted, {skip} skipped, {errors} errors")
    if not args.dry_run:
        remaining = MEDIA_DIR.stat().st_size if MEDIA_DIR.exists() else 0
        size_gb = sum(
            p.stat().st_size for p in MEDIA_DIR.rglob("*") if p.is_file()
        ) / 1_073_741_824
        print(f"Total size after conversion: {size_gb:.2f} GB")


if __name__ == "__main__":
    main()
