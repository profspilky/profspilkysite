"""Import gallery albums and photos from JoomGallery JSON dumps.

JoomGallery stores images at: images/stories/{filename}
So image_local values are written as "images/stories/{filename}",
which maps to media/joomla_images/images/stories/{filename} on disk.

event_date is taken from the earliest photo date inside the album.

Usage:
    python manage.py import_gallery
    python manage.py import_gallery --cats tools/gallery_cats.json
    python manage.py import_gallery --photos tools/gallery.json
    python manage.py import_gallery --clear
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.gallery.models import GalleryAlbum, GalleryPhoto


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt).date()
        except ValueError:
            continue
    return None


def _make_slug(title: str, joomla_id: int) -> str:
    base = slugify(title, allow_unicode=False) or f"album-{joomla_id}"
    return base[:280]


def _photo_local_path(filename: str) -> str:
    """
    JoomGallery saves photos to <joomla_root>/images/stories/<filename>.
    Our media root is media/joomla_images/, so the local path is:
        images/stories/<filename>
    which resolves to:
        media/joomla_images/images/stories/<filename>
    """
    filename = filename.strip()
    if filename.startswith("images/stories/"):
        return filename
    if filename.startswith("stories/"):
        return f"images/{filename}"
    return f"images/stories/{filename}"


class Command(BaseCommand):
    help = "Import JoomGallery albums and photos from JSON dumps."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--cats",
            default="tools/gallery_cats.json",
            help="Path to gallery_cats.json (default: tools/gallery_cats.json)",
        )
        parser.add_argument(
            "--photos",
            default="tools/gallery.json",
            help="Path to gallery.json (default: tools/gallery.json)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing albums/photos before importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only read and validate, do not write to DB.",
        )

    def handle(self, *args, **options) -> None:
        cats_path = Path(options["cats"])
        photos_path = Path(options["photos"])
        dry_run: bool = options["dry_run"]

        if not cats_path.exists():
            raise CommandError(f"File not found: {cats_path}")
        if not photos_path.exists():
            raise CommandError(f"File not found: {photos_path}")

        self.stdout.write("Loading JSON files…")
        cats_data: list[dict] = json.loads(cats_path.read_text(encoding="utf-8"))
        photos_data: list[dict] = json.loads(photos_path.read_text(encoding="utf-8"))

        # Фільтруємо ROOT та неопубліковані
        cats_data = [c for c in cats_data if c.get("parent_id") != "0" and c.get("published") == "1"]
        photos_data = [p for p in photos_data if p.get("published") == "1"]

        self.stdout.write(f"Albums to import: {len(cats_data)}")
        self.stdout.write(f"Photos to import: {len(photos_data)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes written."))
            return

        # Будуємо маппінг catid → найрання дата фото (для event_date альбому)
        earliest_photo_date: dict[str, date | None] = defaultdict(lambda: None)
        for photo in photos_data:
            catid = photo.get("catid", "")
            raw_date = photo.get("date", "")
            d = _parse_date(raw_date)
            if d and (earliest_photo_date[catid] is None or d < earliest_photo_date[catid]):
                earliest_photo_date[catid] = d

        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing gallery data…"))

        with transaction.atomic():
            if options["clear"]:
                GalleryPhoto.objects.all().delete()
                GalleryAlbum.objects.all().delete()
                self.stdout.write(self.style.WARNING("Cleared."))

            album_map: dict[str, GalleryAlbum] = {}
            created_albums = 0
            updated_albums = 0

            for cat in cats_data:
                jid = int(cat["id"])
                title = (cat.get("name") or f"Альбом {jid}").strip()
                alias = (cat.get("alias") or "").strip()
                description = (cat.get("description") or "").strip()

                # event_date береться з найраннішої дати фото в цьому альбомі
                event_date = earliest_photo_date.get(cat["id"])

                slug_base = slugify(alias, allow_unicode=False) if alias else _make_slug(title, jid)
                if not slug_base:
                    slug_base = f"album-{jid}"
                slug = slug_base[:280]

                counter = 2
                original_slug = slug
                while GalleryAlbum.objects.filter(slug=slug).exclude(joomla_id=jid).exists():
                    slug = f"{original_slug[:270]}-{counter}"
                    counter += 1

                obj, created = GalleryAlbum.objects.update_or_create(
                    joomla_id=jid,
                    defaults={
                        "title": title[:255],
                        "slug": slug,
                        "description": description,
                        "event_date": event_date,
                        "is_published": True,
                    },
                )
                album_map[cat["id"]] = obj
                if created:
                    created_albums += 1
                else:
                    updated_albums += 1

            self.stdout.write(f"Albums: {created_albums} created, {updated_albums} updated")

            created_photos = 0
            skipped_photos = 0

            for idx, photo in enumerate(photos_data):
                catid = photo.get("catid", "")
                album = album_map.get(catid)
                if not album:
                    skipped_photos += 1
                    continue

                jid = int(photo["id"])
                filename = (photo.get("filename") or "").strip()
                title = (photo.get("title") or "").strip()

                if not filename:
                    skipped_photos += 1
                    continue

                local_path = _photo_local_path(filename)

                GalleryPhoto.objects.update_or_create(
                    joomla_id=jid,
                    defaults={
                        "album": album,
                        "image_local": local_path,
                        "title": title[:255],
                        "order": idx,
                        "is_published": True,
                    },
                )
                created_photos += 1

                if created_photos % 200 == 0:
                    self.stdout.write(f"  Photos processed: {created_photos}…")

        self.stdout.write(self.style.SUCCESS(
            f"Done! Albums: {created_albums} created, {updated_albums} updated. "
            f"Photos: {created_photos} imported, {skipped_photos} skipped."
        ))

        # Обкладинки: перше фото альбому
        self.stdout.write("Setting album covers…")
        cover_count = 0
        for album in GalleryAlbum.objects.all():
            first_photo = album.photos.filter(is_published=True).order_by("order", "id").first()
            if first_photo and first_photo.image_local:
                album.cover_local = first_photo.image_local
                album.save(update_fields=["cover_local"])
                cover_count += 1
        self.stdout.write(self.style.SUCCESS(f"Set covers for {cover_count} albums."))

        self.stdout.write("")
        self.stdout.write(self.style.WARNING(
            "NOTE: Gallery images must be at media/joomla_images/images/stories/ on disk.\n"
            "      If images are missing, copy them from Joomla server:\n"
            "      scp -r user@server:/path/to/joomla/images/stories/ media/joomla_images/images/stories/"
        ))
