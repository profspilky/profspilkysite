"""
Upload Joomla/local images from media/joomla_images/ to Cloudinary.

Reads image paths from tools/image_paths.txt (built by build_image_paths.py).
Saves original_rel_path → cloudinary_secure_url mapping to tools/image_map.json.
Supports resume: skips already-uploaded paths.
Supports parallel uploads via --workers.

Usage:
    python tools/build_image_paths.py               # build the list first
    python tools/upload_images_cloudinary.py        # upload all (8 workers)
    python tools/upload_images_cloudinary.py --workers 16
    python tools/upload_images_cloudinary.py --limit 200 --dry-run
"""
from __future__ import annotations

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cloudinary
import cloudinary.uploader

BASE = Path(__file__).parent.parent
CLOUDINARY_FOLDER = "fpsu/joomla"
_map_lock = threading.Lock()


def load_env() -> None:
    env_file = BASE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                os.environ[key.strip()] = val.strip()


def _public_id(rel_path: str) -> str:
    """Derive stable Cloudinary public_id: folder/path/stem (no extension)."""
    stem = Path(rel_path).with_suffix("").as_posix()
    return f"{CLOUDINARY_FOLDER}/{stem}"


def _upload_one(
    rel_path: str,
    media_dir: Path,
) -> tuple[str, str | None]:
    """Upload a single file. Returns (rel_path, secure_url_or_None)."""
    local_file = media_dir / rel_path
    if not local_file.exists():
        return rel_path, None
    try:
        result = cloudinary.uploader.upload(
            str(local_file),
            public_id=_public_id(rel_path),
            overwrite=False,
            resource_type="image",
        )
        return rel_path, result["secure_url"]
    except Exception as e:
        return rel_path, f"__error__:{e}"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--paths-file", default=str(BASE / "tools" / "image_paths.txt"))
    parser.add_argument("--media-dir", default=str(BASE / "media" / "joomla_images"))
    parser.add_argument("--output", default=str(BASE / "tools" / "image_map.json"))
    parser.add_argument("--workers", type=int, default=8, help="Parallel upload threads (default 8)")
    parser.add_argument("--limit", type=int, default=0, help="Max images (0=all)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    cloudinary.reset_config()

    if not os.environ.get("CLOUDINARY_URL") and not args.dry_run:
        print("ERROR: CLOUDINARY_URL not set in .env", file=sys.stderr)
        sys.exit(1)

    paths_file = Path(args.paths_file)
    media_dir = Path(args.media_dir)
    output_path = Path(args.output)

    if not paths_file.exists():
        print(f"ERROR: {paths_file} not found. Run build_image_paths.py first.", file=sys.stderr)
        sys.exit(1)

    # Resume: load existing map
    image_map: dict[str, str] = {}
    if output_path.exists():
        try:
            image_map = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        print(f"Resuming: {len(image_map)} already uploaded.")

    all_paths = [p.strip() for p in paths_file.read_text(encoding="utf-8").splitlines() if p.strip()]
    # Skip already done
    pending = [p for p in all_paths if p not in image_map]

    if args.limit:
        pending = pending[: args.limit]

    total_all = len(all_paths)
    total_pending = len(pending)
    print(f"Total: {total_all}, already uploaded: {len(image_map)}, to upload: {total_pending}")

    if not pending:
        print("Nothing to do.")
        return

    if args.dry_run:
        print(f"DRY RUN ({args.workers} workers) — first 10:")
        for p in pending[:10]:
            print(f"  {p} → {_public_id(p)}")
        return

    print(f"Starting upload with {args.workers} workers …")

    uploaded = failed = 0

    def _save() -> None:
        output_path.write_text(
            json.dumps(image_map, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_upload_one, p, media_dir): p for p in pending}
        for future in as_completed(futures):
            rel_path, result = future.result()

            with _map_lock:
                if result and not result.startswith("__error__:"):
                    image_map[rel_path] = result
                    uploaded += 1
                else:
                    failed += 1
                    if result:
                        err = result.replace("__error__:", "")
                        print(f"  FAIL {rel_path}: {err}")

                done = uploaded + failed
                if done % 50 == 0:
                    _save()
                    pct = 100 * (len(image_map)) // total_all
                    print(
                        f"  [{pct}%] {len(image_map)}/{total_all} total | "
                        f"+{uploaded} uploaded, {failed} failed this run"
                    )

    _save()
    print(f"\nDone. Uploaded: {uploaded}, Failed: {failed}")
    print(f"Total in map: {len(image_map)} / {total_all}")
    print(f"Map saved → {output_path}")


if __name__ == "__main__":
    main()
