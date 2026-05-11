"""
Management command: download gallery images from Joomla server and upload to Cloudinary.

JoomGallery stores originals at:
    <joomla_root>/images/stories/<filename>

For each GalleryPhoto with empty `image` CloudinaryField this command:
  1. Downloads the file via SCP from the Joomla server
  2. Uploads it to Cloudinary under fpsu/gallery/
  3. Saves the public_id back to GalleryPhoto.image
  4. If the photo is the first in its album, also updates GalleryAlbum.cover_image

Prerequisites:
  - SSH key at key_dig_priv.pem (or set --ssh-key)
  - Cloudinary credentials in environment (CLOUDINARY_CLOUD_NAME, etc.)

Usage:
    python manage.py upload_gallery_to_cloudinary
    python manage.py upload_gallery_to_cloudinary --limit 50
    python manage.py upload_gallery_to_cloudinary --album-id 123
    python manage.py upload_gallery_to_cloudinary --dry-run
"""
from __future__ import annotations

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
REMOTE_BASE = "/sites/www.fpsu.org.ua"
SSH_HOST = "78.27.236.224"
SSH_PORT = "9092"
SSH_USER = "root"
CLOUDINARY_FOLDER = "fpsu/gallery"


class Command(BaseCommand):
    help = "Download JoomGallery images via SCP and upload to Cloudinary"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--ssh-key", default=str(DEFAULT_KEY))
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
        limit: int = options["limit"]
        album_pk: int | None = options.get("album_id")
        dry_run: bool = options["dry_run"]

        if not dry_run and not key_path.exists():
            raise CommandError(f"SSH key not found: {key_path}")

        qs = GalleryPhoto.objects.select_related("album").filter(is_published=True)

        if album_pk:
            qs = qs.filter(album__pk=album_pk)

        # Skip photos already uploaded unless re-upload is requested
        if options["skip_existing"]:
            qs = qs.filter(image="")

        qs = qs.order_by("album_id", "order", "id")

        total = qs.count()
        self.stdout.write(f"Photos to process: {total}")
        if limit:
            self.stdout.write(f"Limit: {limit}")

        processed = uploaded = errors = skipped = 0

        # Track which albums need cover updates (first photo in album)
        album_first_photo: dict[int, GalleryPhoto] = {}

        for photo in qs.iterator():
            if limit and processed >= limit:
                break

            if not photo.image_local:
                skipped += 1
                processed += 1
                continue

            # image_local = "images/stories/<filename>"
            # Remote path = REMOTE_BASE/images/stories/<filename>
            remote_path = f"{REMOTE_BASE}/{photo.image_local}"
            filename = Path(photo.image_local).name
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
                        self.style.ERROR(f"  SCP failed [{photo.pk}]: {photo.image_local}")
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

                    # Track first photo per album for cover update
                    if photo.album_id not in album_first_photo:
                        album_first_photo[photo.album_id] = photo

                    if uploaded % 50 == 0:
                        self.stdout.write(f"  {uploaded} uploaded…")

                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"  Cloudinary error [{photo.pk}]: {exc}"))
                    errors += 1

            processed += 1

        # Update album covers from first successfully uploaded photo
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
                f"{skipped} skipped (no local path), {processed} processed"
            )
        )
