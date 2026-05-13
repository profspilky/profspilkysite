"""
Management command: upload gallery images to Cloudinary by fetching from fpsu.org.ua.

For each GalleryPhoto / GalleryAlbum whose image/cover_image is empty,
constructs the original Joomla URL from image_local / cover_local and
uploads it directly to Cloudinary (Cloudinary fetches the URL itself).

Usage:
    python manage.py fetch_gallery_from_web --dry-run
    python manage.py fetch_gallery_from_web --limit 50
    python manage.py fetch_gallery_from_web
    python manage.py fetch_gallery_from_web --workers 8
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.gallery.models import GalleryAlbum, GalleryPhoto

JOOMLA_BASE = "https://www.fpsu.org.ua"
CDN_FOLDER = "fpsu/gallery"


def _load_env() -> None:
    env_file = Path(__file__).resolve().parents[4] / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def _public_id(local_path: str, album_slug: str) -> str:
    stem = Path(local_path).stem
    return f"{CDN_FOLDER}/{album_slug}/{stem}"


def _upload_url(url: str, public_id: str) -> str:
    """Upload image from URL to Cloudinary. Returns secure_url."""
    result = cloudinary.uploader.upload(
        url,
        public_id=public_id,
        overwrite=False,
        resource_type="image",
        invalidate=True,
    )
    return result["secure_url"]


class Command(BaseCommand):
    help = "Fetch gallery images from fpsu.org.ua and upload to Cloudinary"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--limit", type=int, default=0, help="Max photos (0=all)")
        parser.add_argument("--workers", type=int, default=8, help="Parallel threads")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        _load_env()
        cloudinary.reset_config()

        limit: int = options["limit"]
        workers: int = options["workers"]
        dry_run: bool = options["dry_run"]

        self._process_photos(limit, workers, dry_run)
        self._process_covers(dry_run)

        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.flush()

    # ── Photos ───────────────────────────────────────────────────────────────

    def _process_photos(self, limit: int, workers: int, dry_run: bool) -> None:
        qs = (
            GalleryPhoto.objects.filter(Q(image__isnull=True) | Q(image=""))
            .select_related("album")
            .order_by("album_id", "id")
        )
        total = qs.count()
        self.stdout.write(f"Photos without Cloudinary image: {total}")
        if limit:
            qs = qs[:limit]

        items = list(qs)
        if not items:
            return

        uploaded = errors = 0

        def _process_photo(photo: GalleryPhoto) -> tuple[int, str | None, str | None]:
            if not photo.image_local:
                return photo.pk, None, "no image_local"
            url = f"{JOOMLA_BASE}/{photo.image_local}"
            pub_id = _public_id(photo.image_local, photo.album.slug)
            if dry_run:
                return photo.pk, url, None
            try:
                cdn_url = _upload_url(url, pub_id)
                return photo.pk, cdn_url, None
            except Exception as exc:
                return photo.pk, None, str(exc)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process_photo, p): p for p in items}
            done = 0
            batch_save: list[GalleryPhoto] = []

            for future in as_completed(futures):
                done += 1
                pk, cdn_url, err = future.result()
                if err:
                    errors += 1
                    if errors <= 5:
                        print(f"  ERR photo {pk}: {err[:120]}", flush=True)
                elif cdn_url and not dry_run:
                    photo = futures[future]
                    photo.image = cdn_url
                    batch_save.append(photo)
                    uploaded += 1

                if len(batch_save) >= 50 or (done == len(items) and batch_save):
                    if not dry_run:
                        with transaction.atomic():
                            GalleryPhoto.objects.bulk_update(batch_save, ["image"])
                    batch_save.clear()

                if done % 50 == 0 or done == len(items):
                    print(
                        f"  photos: {done}/{len(items)} done | uploaded={uploaded} errors={errors}",
                        flush=True,
                    )

        self.stdout.write(f"  → {uploaded} photos uploaded, {errors} errors")
        self.stdout.flush()

    # ── Album covers ─────────────────────────────────────────────────────────

    def _process_covers(self, dry_run: bool) -> None:
        qs = GalleryAlbum.objects.filter(
            Q(cover_image__isnull=True) | Q(cover_image="")
        ).exclude(cover_local="").order_by("id")
        total = qs.count()
        self.stdout.write(f"Albums without cover: {total}")

        uploaded = errors = 0
        for album in qs:
            url = f"{JOOMLA_BASE}/{album.cover_local}"
            pub_id = _public_id(album.cover_local, album.slug)
            if dry_run:
                print(f"  DRY album {album.pk}: {url}", flush=True)
                continue
            try:
                cdn_url = _upload_url(url, pub_id)
                GalleryAlbum.objects.filter(pk=album.pk).update(cover_image=cdn_url)
                uploaded += 1
            except Exception as exc:
                errors += 1
                if errors <= 5:
                    print(f"  ERR album {album.pk}: {str(exc)[:120]}", flush=True)

        self.stdout.write(f"  → {uploaded} album covers uploaded, {errors} errors")
        self.stdout.flush()
