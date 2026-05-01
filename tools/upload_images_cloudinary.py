"""Upload Joomla images from image_paths.txt to Cloudinary.

Reads CLOUDINARY_URL from .env or environment.
Saves mapping original_path → cloudinary_url to tools/image_map.json.

Usage:
    python tools/upload_images_cloudinary.py
    python tools/upload_images_cloudinary.py --limit 100 --dry-run
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import cloudinary
import cloudinary.uploader


def load_env() -> None:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--paths-file", default="tools/image_paths.txt")
    parser.add_argument("--media-dir", default="media/joomla_images")
    parser.add_argument("--output", default="tools/image_map.json")
    parser.add_argument("--limit", type=int, default=0, help="Max images to upload (0=all)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()

    cloudinary_url = os.environ.get("CLOUDINARY_URL", "")
    if not cloudinary_url and not args.dry_run:
        print("ERROR: CLOUDINARY_URL not set in environment.", file=sys.stderr)
        sys.exit(1)

    if cloudinary_url:
        cloudinary.config(from_url=cloudinary_url)

    paths_file = Path(args.paths_file)
    media_dir = Path(args.media_dir)
    output_path = Path(args.output)

    if not paths_file.exists():
        print(f"ERROR: {paths_file} not found.", file=sys.stderr)
        sys.exit(1)

    # Завантажуємо існуючий маппінг (продовжуємо якщо переривались)
    image_map: dict[str, str] = {}
    if output_path.exists():
        image_map = json.loads(output_path.read_text(encoding="utf-8"))
        print(f"Loaded existing map with {len(image_map)} entries.")

    paths = [p.strip() for p in paths_file.read_text(encoding="utf-8").splitlines() if p.strip()]

    if args.limit:
        paths = paths[: args.limit]

    print(f"Total paths to process: {len(paths)}")

    uploaded = 0
    skipped = 0
    failed = 0

    for idx, rel_path in enumerate(paths):
        # Пропускаємо вже завантажені
        if rel_path in image_map:
            skipped += 1
            continue

        local_file = media_dir / rel_path
        if not local_file.exists():
            skipped += 1
            continue

        if args.dry_run:
            image_map[rel_path] = f"https://cloudinary.example.com/{rel_path}"
            uploaded += 1
            continue

        try:
            result = cloudinary.uploader.upload(
                str(local_file),
                folder="fpsu/joomla",
                use_filename=True,
                unique_filename=False,
                overwrite=False,
                resource_type="image",
            )
            image_map[rel_path] = result["secure_url"]
            uploaded += 1
        except Exception as e:
            print(f"  FAIL [{idx}] {rel_path}: {e}")
            failed += 1

        # Зберігаємо маппінг кожні 50 завантажень (відновлення після збою)
        if (uploaded + failed) % 50 == 0:
            output_path.write_text(json.dumps(image_map, ensure_ascii=False, indent=None), encoding="utf-8")
            print(f"  Progress: {uploaded} uploaded, {skipped} skipped, {failed} failed")

    # Фінальне збереження
    output_path.write_text(json.dumps(image_map, ensure_ascii=False, indent=None), encoding="utf-8")
    print(f"\nDone! Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}")
    print(f"Map saved to {output_path}")


if __name__ == "__main__":
    main()
