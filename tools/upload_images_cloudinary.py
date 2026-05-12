"""
Upload Joomla/local images from media/joomla_images/ to Cloudinary.

Reads image paths from tools/image_paths.txt (built by build_image_paths.py).
Saves original_rel_path → cloudinary_secure_url mapping to tools/image_map.json.
Supports resume: skips already-uploaded paths.
Supports parallel uploads via --workers.

Cross-process safety:
  - Exclusive flock on tools/.upload_images_cloudinary.lock so two terminals
    cannot overwrite each other's image_map.json.
  - Atomic save (temp file + os.replace) to avoid corrupt JSON on crash.

Usage:
    python tools/build_image_paths.py               # build the list first
    python tools/upload_images_cloudinary.py        # default: 1000 files (тест), 12 workers
    python tools/upload_images_cloudinary.py --limit 0   # усі файли з image_paths.txt
    python tools/upload_images_cloudinary.py --workers 20
    python tools/upload_images_cloudinary.py --dry-run
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import IO

import cloudinary
import cloudinary.uploader

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:
    fcntl = None  # type: ignore[assignment]
    _HAS_FCNTL = False

BASE = Path(__file__).parent.parent
CLOUDINARY_FOLDER = "fpsu/joomla"
_map_lock = threading.Lock()
_LOCK_PATH = BASE / "tools" / ".upload_images_cloudinary.lock"
_SAVE_EVERY = 100


def load_env() -> None:
    env_file = BASE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def _acquire_run_lock() -> IO[str] | None:
    """
    Block until exclusive lock (only one upload process).
    Returns open file handle — keep open until upload finishes.
    """
    if not _HAS_FCNTL:
        return None
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fp = open(_LOCK_PATH, "w", encoding="utf-8")
    fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
    fp.write(f"pid={os.getpid()}\n")
    fp.flush()
    return fp


def _release_run_lock(fp: IO[str] | None) -> None:
    if fp is None or not _HAS_FCNTL:
        return
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    fp.close()


def _load_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _atomic_write_json(path: Path, data: dict[str, str]) -> None:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    fd, tmp = tempfile.mkstemp(
        dir=path.parent, prefix=".image_map_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _public_id(rel_path: str) -> str:
    stem = Path(rel_path).with_suffix("").as_posix()
    return f"{CLOUDINARY_FOLDER}/{stem}"


def _upload_one(rel_path: str, media_dir: Path) -> tuple[str, str | None]:
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
    parser.add_argument(
        "--workers",
        type=int,
        default=12,
        help="Parallel upload threads (default 12)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Max new uploads this run (default 1000 for tests). Use 0 for all remaining.",
    )
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

    lock_fp: IO[str] | None = None
    if not args.dry_run:
        if _HAS_FCNTL:
            print("Очікування блокування (інший upload не може перезаписати map) …", flush=True)
            lock_fp = _acquire_run_lock()
        else:
            print("WARNING: fcntl недоступний — не запускай два upload одночасно.", flush=True)

    try:
        # Після lock — свіжа карта з диску (один письменник)
        image_map = _load_map(output_path)
        print(f"Resuming: {len(image_map)} already in map.", flush=True)

        all_paths = [
            p.strip()
            for p in paths_file.read_text(encoding="utf-8").splitlines()
            if p.strip()
        ]
        pending = [p for p in all_paths if p not in image_map]

        limit_run = None if args.limit == 0 else args.limit
        if limit_run is not None:
            pending = pending[:limit_run]

        total_all = len(all_paths)
        total_pending = len(pending)
        cap_msg = " (усі)" if limit_run is None else f" (макс. {limit_run} за цей запуск)"
        print(
            f"У списку: {total_all}, уже в map: {len(image_map)}, "
            f"завантажити зараз: {total_pending}{cap_msg}",
            flush=True,
        )

        if not pending:
            print("Nothing to do.", flush=True)
            return

        if args.dry_run:
            print(f"DRY RUN ({args.workers} workers) — first 10:", flush=True)
            for p in pending[:10]:
                print(f"  {p} → {_public_id(p)}", flush=True)
            return

        print(f"Starting upload with {args.workers} workers …", flush=True)

        uploaded = failed = 0

        def _save() -> None:
            _atomic_write_json(output_path, image_map)

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
                            print(f"  FAIL {rel_path}: {err}", flush=True)

                    done = uploaded + failed
                    if done % _SAVE_EVERY == 0:
                        _save()
                        run_pct = 100 * done // total_pending if total_pending else 100
                        print(
                            f"  [run {run_pct}%] +{uploaded}/{total_pending} this run | "
                            f"map total {len(image_map)}/{total_all} | fail {failed}",
                            flush=True,
                        )

        _save()
        print(f"\nDone. Uploaded: {uploaded}, Failed: {failed}", flush=True)
        print(f"Total in map: {len(image_map)} / {total_all}", flush=True)
        print(f"Map saved → {output_path}", flush=True)
    finally:
        _release_run_lock(lock_fp)


if __name__ == "__main__":
    main()
