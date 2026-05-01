"""
Management command: download article images from Joomla server and upload to Cloudinary.

For each Article with a non-empty Joomla image path (stored in tools/articles.tsv images field),
this command:
  1. SCP-downloads the file from /sites/www.fpsu.org.ua/images/<path>
  2. Uploads it to Cloudinary under the folder 'fpsu/news/'
  3. Updates Article.image with the Cloudinary resource

Prerequisites:
  - SSH key at tools/../key_dig_priv.pem (or set --ssh-key)
  - Cloudinary credentials set in environment (CLOUDINARY_CLOUD_NAME etc.)

Usage:
    python manage.py import_images
    python manage.py import_images --limit 100
    python manage.py import_images --article-id 29093
    python manage.py import_images --ssh-key /path/to/key.pem
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand, CommandError

from apps.news.models import Article

BASE = Path(__file__).resolve().parents[4]
DEFAULT_KEY = BASE / "key_dig_priv.pem"
DEFAULT_ARTS_TSV = BASE / "tools" / "articles.tsv"
REMOTE_BASE = "/sites/www.fpsu.org.ua"
SSH_HOST = "78.27.236.224"
SSH_PORT = "9092"
SSH_USER = "root"
CLOUDINARY_FOLDER = "fpsu/news"

_IMG_FIELDS = ("image_intro", "image_fulltext")


def _extract_image_intro(images_json: str) -> str:
    if not images_json or images_json in ("NULL", ""):
        return ""
    try:
        data = json.loads(images_json)
    except json.JSONDecodeError:
        return ""
    for field in _IMG_FIELDS:
        val = data.get(field, "")
        if val and val.strip():
            return val.strip()
    return ""


def _read_tsv(path: Path, num_cols: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) < num_cols:
            continue
        if len(parts) > num_cols:
            parts = parts[: num_cols - 1] + ["\t".join(parts[num_cols - 1 :])]
        rows.append(parts)
    return rows


class Command(BaseCommand):
    help = "Download Joomla article images via SCP and upload to Cloudinary"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--ssh-key", default=str(DEFAULT_KEY))
        parser.add_argument("--arts-tsv", default=str(DEFAULT_ARTS_TSV))
        parser.add_argument("--limit", type=int, default=0, help="Max images to process (0=all)")
        parser.add_argument("--article-id", type=int, help="Process only this Joomla ID")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        key_path = Path(options["ssh_key"])
        arts_tsv = Path(options["arts_tsv"])
        limit: int = options["limit"]
        target_id: int | None = options.get("article_id")
        dry_run: bool = options["dry_run"]

        if not key_path.exists():
            raise CommandError(f"SSH key not found: {key_path}")
        if not arts_tsv.exists():
            raise CommandError(f"TSV not found: {arts_tsv}")

        # Build joomla_id → image_path map from TSV
        img_map: dict[int, str] = {}
        for row in _read_tsv(arts_tsv, 8):
            jid, _, _, _, _, _, images_json, _ = row
            if not jid or jid == "NULL":
                continue
            img_path = _extract_image_intro(images_json)
            if img_path:
                img_map[int(jid)] = img_path

        if target_id:
            img_map = {k: v for k, v in img_map.items() if k == target_id}

        self.stdout.write(f"Articles with images: {len(img_map)}")

        processed = 0
        ok = 0
        errors = 0

        for jid, img_path in img_map.items():
            if limit and processed >= limit:
                break

            # Skip if Article already has an image
            try:
                art = Article.objects.get(joomla_id=jid)
            except Article.DoesNotExist:
                self.stdout.write(f"  SKIP (not in DB): joomla_id={jid}")
                continue

            if art.image:
                processed += 1
                continue

            remote_path = f"{REMOTE_BASE}/{img_path}"
            public_id = f"{CLOUDINARY_FOLDER}/{jid}-{Path(img_path).stem}"

            if dry_run:
                self.stdout.write(f"  DRY: {remote_path} → {public_id}")
                processed += 1
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                local_file = Path(tmpdir) / Path(img_path).name
                scp_cmd = [
                    "scp",
                    "-i", str(key_path),
                    "-P", SSH_PORT,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    f"{SSH_USER}@{SSH_HOST}:{remote_path}",
                    str(local_file),
                ]
                result = subprocess.run(scp_cmd, capture_output=True)
                if result.returncode != 0 or not local_file.exists():
                    self.stdout.write(
                        self.style.ERROR(f"  SCP failed: {img_path}")
                    )
                    errors += 1
                    processed += 1
                    continue

                try:
                    upload_result = cloudinary.uploader.upload(
                        str(local_file),
                        public_id=public_id,
                        folder="",
                        overwrite=False,
                        resource_type="image",
                    )
                    art.image = upload_result["public_id"]
                    art.save(update_fields=["image"])
                    ok += 1
                    self.stdout.write(f"  OK [{jid}] {img_path}")
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"  Cloudinary error [{jid}]: {exc}"))
                    errors += 1

            processed += 1

        self.stdout.write(
            self.style.SUCCESS(f"Done: {ok} uploaded, {errors} errors, {processed} processed")
        )
