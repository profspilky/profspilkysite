"""
Management command: download gallery images from Joomla server and upload to Cloudinary.

JoomGallery config (confirmed from MySQL zeki2_joomgallery_config):
    jg_pathoriginalimages = 'images/joomgallery/originals/'
    jg_paththumbs         = 'images/joomgallery/thumbnails/'

Full remote path:
    <joomla_root>/images/joomgallery/originals/<catpath>/<filename>

catpath per album is read from tools/gallery_cats.json (field: "catpath").
Joomla root confirmed from configuration.php: /home/www/data/www.fpsu.org.ua

For each GalleryPhoto with empty `image` CloudinaryField this command:
  1. Downloads the file via SCP from the Joomla server
  2. Uploads it to Cloudinary under fpsu/gallery/
  3. Saves the public_id back to GalleryPhoto.image
  4. Updates GalleryAlbum.cover_image from the first successfully uploaded photo

Prerequisites:
  - SSH key at key_dig_priv.pem (or set --ssh-key)
  - Cloudinary credentials in environment (CLOUDINARY_CLOUD_NAME, etc.)
  - tools/gallery_cats.json present (for catpath lookup)

Usage:
    python manage.py upload_gallery_to_cloudinary --dry-run --limit 5
    python manage.py upload_gallery_to_cloudinary --limit 100
    python manage.py upload_gallery_to_cloudinary
    python manage.py upload_gallery_to_cloudinary --album-id 123
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

from apps.gallery.models import GalleryAlbum, GalleryPhoto

BASE = Path(__file__).resolve().parents[4]
DEFAULT_KEY = BASE / "key_dig_priv.pem"
DEFAULT_CATS_JSON = BASE / "tools" / "gallery_cats.json"

# Correct Joomla root (confirmed from /home/www/data/www.fpsu.org.ua/configuration.php)
REMOTE_BASE = "/home/www/data/www.fpsu.org.ua"
JOOMGALLERY_ORIGINALS = "images/joomgallery/originals"

SSH_HOST = "78.27.236.224"
SSH_PORT = "9092"
SSH_USER = "root"
CLOUDINARY_FOLDER = "fpsu/gallery"


def _load_catpath_map(cats_json: Path) -> dict[int, str]:
    """Return {joomla_cat_id: catpath} from gallery_cats.json."""
    if not cats_json.exists():
        return {}
    cats = json.loads(cats_json.read_text(encoding="utf-8"))
    return {int(c["id"]): (c.get("catpath") or "").strip() for c in cats if c.get("id")}


class Command(BaseCommand):
    help = "Download JoomGallery images via SCP and upload to Cloudinary"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--ssh-key", default=str(DEFAULT_KEY))
        parser.add_argument(
            "--cats-json",
            default=str(DEFAULT_CATS_JSON),
            help="Path to gallery_cats.json for catpath lookup",
        )
        parser.add_argument("--limit", type=int, default=0, help="Max photos to process (0=all)")
        parser.add_argument("--album-id", type=int, help="Process only this album (GalleryAlbum pk)")
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=True,
            help="Skip photos that already have a Cloudinary image (default: True)",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        key_path = Path(options["ssh_key"])
        cats_json = Path(options["cats_json"])
        limit: int = options["limit"]
        album_pk: int | None = options.get("album_id")
        dry_run: bool = options["dry_run"]

        if not dry_run and not key_path.exists():
            raise CommandError(f"SSH key not found: {key_path}")

        catpath_map = _load_catpath_map(cats_json)
        if not catpath_map:
            raise CommandError(f"gallery_cats.json not found at {cats_json}")

        self.stdout.write(f"Catpath map loaded: {len(catpath_map)} albums")

        qs = GalleryPhoto.objects.select_related("album").filter(is_published=True)

        if album_pk:
            qs = qs.filter(album__pk=album_pk)

        if options["skip_existing"]:
            qs = qs.filter(image="")

        qs = qs.order_by("album_id", "order", "id")

        total = qs.count()
        self.stdout.write(f"Photos to process: {total}")
        if limit:
            self.stdout.write(f"Limit: {limit}")

        processed = uploaded = errors = skipped = 0
        album_first_photo: dict[int, GalleryPhoto] = {}

        for photo in qs.iterator():
            if limit and processed >= limit:
                break

            filename = Path(photo.image_local).name if photo.image_local else ""
            if not filename:
                skipped += 1
                processed += 1
                continue

            # Build correct remote path:
            # /home/www/data/www.fpsu.org.ua/images/joomgallery/originals/<catpath>/<filename>
            joomla_cat_id = photo.album.joomla_id or 0
            catpath = catpath_map.get(joomla_cat_id, "")
            if not catpath:
                self.stdout.write(self.style.WARNING(
                    f"  No catpath for album joomla_id={joomla_cat_id} (pk={photo.album_id}), skipping"
                ))
                skipped += 1
                processed += 1
                continue

            remote_path = f"{REMOTE_BASE}/{JOOMGALLERY_ORIGINALS}/{catpath}/{filename}"
            public_id = f"{CLOUDINARY_FOLDER}/{photo.album.slug}/{filename}"

            if dry_run:
                self.stdout.write(f"  DRY [{photo.pk}] {remote_path} → {public_id}")
                processed += 1
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                local_file = Path(tmpdir) / filename
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
                        self.style.ERROR(f"  SCP failed [{photo.pk}]: {remote_path}")
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
                    photo.image = upload_result["public_id"]
                    photo.save(update_fields=["image"])
                    uploaded += 1

                    if photo.album_id not in album_first_photo:
                        album_first_photo[photo.album_id] = photo

                    if uploaded % 50 == 0:
                        self.stdout.write(f"  {uploaded} uploaded…")

                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"  Cloudinary error [{photo.pk}]: {exc}"))
                    errors += 1

            processed += 1

        if not dry_run and album_first_photo:
            cover_updated = 0
            for album_id, photo in album_first_photo.items():
                if photo.image:
                    GalleryAlbum.objects.filter(pk=album_id).update(cover_image=photo.image)
                    cover_updated += 1
            self.stdout.write(f"Album covers updated: {cover_updated}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {uploaded} uploaded, {errors} errors, "
                f"{skipped} skipped, {processed} processed"
            )
        )
