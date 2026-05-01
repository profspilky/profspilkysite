"""Import gallery albums and photos from JoomGallery JSON dumps.

Usage:
    python manage.py import_gallery
    python manage.py import_gallery --cats tools/gallery_cats.json
    python manage.py import_gallery --photos tools/gallery.json
    python manage.py import_gallery --clear
"""
from __future__ import annotations

import json
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
    # Обрізаємо до 280 символів
    return base[:280]


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

        # Фільтруємо ROOT та неопубліковані категорії
        cats_data = [c for c in cats_data if c.get("parent_id") != "0" and c.get("published") == "1"]
        photos_data = [p for p in photos_data if p.get("published") == "1"]

        self.stdout.write(f"Albums to import: {len(cats_data)}")
        self.stdout.write(f"Photos to import: {len(photos_data)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes written."))
            return

        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing gallery data…"))
            GalleryPhoto.objects.all().delete()
            GalleryAlbum.objects.all().delete()

        with transaction.atomic():
            album_map: dict[str, GalleryAlbum] = {}
            created_albums = 0
            updated_albums = 0

            for cat in cats_data:
                jid = int(cat["id"])
                title = (cat.get("name") or f"Альбом {jid}").strip()
                alias = (cat.get("alias") or "").strip()
                description = (cat.get("description") or "").strip()
                event_date = _parse_date(None)

                # Формуємо slug
                slug_base = slugify(alias, allow_unicode=False) if alias else _make_slug(title, jid)
                if not slug_base:
                    slug_base = f"album-{jid}"
                slug = slug_base[:280]

                # Унікалізуємо slug при колізії
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

                # Шлях у joomla_images/
                local_path = f"stories/{filename}" if not filename.startswith("stories/") else filename

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

        # Встановлення обкладинок: перше фото альбому
        self.stdout.write("Setting album covers…")
        cover_count = 0
        for album in GalleryAlbum.objects.all():
            first_photo = album.photos.filter(is_published=True).order_by("order", "id").first()
            if first_photo and first_photo.image_local and not album.cover_local:
                album.cover_local = first_photo.image_local
                album.save(update_fields=["cover_local"])
                cover_count += 1
        self.stdout.write(self.style.SUCCESS(f"Set covers for {cover_count} albums."))
