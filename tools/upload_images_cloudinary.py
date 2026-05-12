"""
Upload Joomla/local images from media/joomla_images/ to Cloudinary.

Reads image paths from tools/image_paths.txt (built by build_image_paths.py).
Saves original_rel_path → cloudinary_secure_url mapping to tools/image_map.json.
Supports resume: skips already-uploaded paths.

Usage:
    python tools/build_image_paths.py           # build the list first
    python tools/upload_images_cloudinary.py    # upload all
    python tools/upload_images_cloudinary.py --limit 200 --dry-run
    python tools/upload_images_cloudinary.py --limit 200   # resume-safe
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import cloudinary
import cloudinary.uploader

BASE = Path(__file__).parent.parent
CLOUDINARY_FOLDER = "fpsu/joomla"


def load_env() -> None:
    env_file = BASE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def _public_id(rel_path: str) -> str:
    """Derive stable Cloudinary public_id: folder/path/stem (no extension)."""
    p = Path(rel_path)
    stem = p.with_suffix("").as_posix()
    return f"{CLOUDINARY_FOLDER}/{stem}"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--paths-file", default=str(BASE / "tools" / "image_paths.txt"))
    parser.add_argument("--media-dir", default=str(BASE / "media" / "joomla_images"))
    parser.add_argument("--output", default=str(BASE / "tools" / "image_map.json"))
    parser.add_argument("--limit", type=int, default=0, help="Max images (0=all)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()

    cloudinary_url = os.environ.get("CLOUDINARY_URL", "")
    if cloudinary_url:
        cloudinary.config(from_url=cloudinary_url)
    elif not args.dry_run:
        print("ERROR: CLOUDINARY_URL not set.", file=sys.stderr)
        sys.exit(1)

    paths_file = Path(args.paths_file)
    media_dir = Path(args.media_dir)
    output_path = Path(args.output)

    if not paths_file.exists():
        print(f"ERROR: {paths_file} not found. Run build_image_paths.py first.", file=sys.stderr)
        sys.exit(1)

    # Load existing map (resume support)
    image_map: dict[str, str] = {}
    if output_path.exists():
        image_map = json.loads(output_path.read_text(encoding="utf-8"))
        print(f"Resuming: {len(image_map)} already uploaded.")

    paths = [p.strip() for p in paths_file.read_text(encoding="utf-8").splitlines() if p.strip()]
    if args.limit:
        paths = paths[: args.limit]

    print(f"Total paths: {len(paths)}, to process: {len(paths) - len(image_map)}")

    uploaded = skipped = failed = 0

    for idx, rel_path in enumerate(paths):
        if rel_path in image_map:
            skipped += 1
            continue

        local_file = media_dir / rel_path
        if not local_file.exists():
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY [{idx}] {rel_path} → {_public_id(rel_path)}")
            uploaded += 1
            if uploaded >= 20:
                print("  … (dry-run limited to 20)")
                break
            continue

        try:
            result = cloudinary.uploader.upload(
                str(local_file),
                public_id=_public_id(rel_path),
                overwrite=False,
                resource_type="image",
            )
            image_map[rel_path] = result["secure_url"]
            uploaded += 1
        except Exception as e:
            print(f"  FAIL [{idx}] {rel_path}: {e}")
            failed += 1

        if (uploaded + failed) % 50 == 0:
            output_path.write_text(
                json.dumps(image_map, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            print(f"  Progress: {uploaded} uploaded, {skipped} skipped, {failed} failed")

    output_path.write_text(
        json.dumps(image_map, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"\nDone. Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}")
    print(f"Map saved → {output_path}")


if __name__ == "__main__":
    main()
