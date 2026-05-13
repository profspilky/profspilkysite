"""
Management command: apply Cloudinary image map to articles and static pages.

Reads tools/image_map.json (built by tools/upload_images_cloudinary.py) and:

  1. Rewrites Article.body — replaces:
       src="https://www.fpsu.org.ua/images/<PATH>"
       src="https://fpsu.org.ua/images/<PATH>"   (без www)
       or src="/images/<PATH>"
     with the Cloudinary URL from the map. Query string (?…) у шляху відкидається.

  2. Sets Article.image — перше зображення в body, якщо для нього є map.

  3. Rewrites StaticPage.body in the same way.

Idempotent: safe to re-run.

Usage:
    python manage.py apply_cloudinary_map --dry-run
    python manage.py apply_cloudinary_map
    python manage.py apply_cloudinary_map --skip-body
    python manage.py apply_cloudinary_map --skip-covers
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.gallery.models import GalleryAlbum, GalleryPhoto
from apps.news.models import Article
from apps.pages.models import StaticPage

BASE = Path(__file__).resolve().parents[4]
DEFAULT_MAP = BASE / "tools" / "image_map.json"


def _write_out(cmd: BaseCommand, msg: str) -> None:
    cmd.stdout.write(msg)
    cmd.stdout.flush()

# Абсолютні URL fpsu (з www або без) + відносні /images/…
_FPSU_RE = re.compile(
    r'(src|href)="(https?://(?:www\.)?fpsu\.org\.ua/images/([^"?#]+)|/?images/'
    r'([^"?#]+\.(?:jpe?g|png|gif|bmp|webp|tiff?)))"',
    re.IGNORECASE,
)


def _path_from_match(m: re.Match[str]) -> str:
    """Шлях після /images/ без query/fragment."""
    raw = (m.group(3) or m.group(4) or "").lstrip("/")
    return unquote(raw.split("#", 1)[0].strip())


def _to_webp(path_str: str) -> str:
    p = Path(path_str)
    if p.suffix.lower() == ".webp":
        return str(p)
    return str(p.with_suffix(".webp"))


class Command(BaseCommand):
    help = "Apply Cloudinary image map to Article/StaticPage bodies and cover fields"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--image-map",
            default=str(DEFAULT_MAP),
            help="Path to tools/image_map.json",
        )
        parser.add_argument("--batch", type=int, default=500)
        parser.add_argument(
            "--skip-body",
            action="store_true",
            help="Skip body HTML rewrite (covers only)",
        )
        parser.add_argument(
            "--skip-covers",
            action="store_true",
            help="Skip Article.image update (body rewrite only)",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--gallery",
            action="store_true",
            help="Also update GalleryAlbum.cover_image and GalleryPhoto.image from map",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        map_path = Path(options["image_map"])
        batch: int = options["batch"]
        skip_body: bool = options["skip_body"]
        skip_covers: bool = options["skip_covers"]
        dry_run: bool = options["dry_run"]
        gallery: bool = options["gallery"]

        if not map_path.exists():
            raise CommandError(
                f"image_map.json not found at {map_path}.\n"
                "Run: python tools/build_image_paths.py && "
                "python tools/upload_images_cloudinary.py"
            )

        image_map: dict[str, str] = json.loads(map_path.read_text(encoding="utf-8"))
        _write_out(self, f"Image map loaded: {len(image_map)} entries.")

        def _lookup(path_str: str) -> str | None:
            """Look up Cloudinary URL for an images/ relative path (any extension).

            Joomla URLs frequently use double prefix:
            /images/images/2020/... → map key is images/images/2020/...
            So we always try both with and without extra images/ prefix.
            """
            clean = path_str.lstrip("/")
            # 1. direct
            if clean in image_map:
                return image_map[clean]
            # 2. webp variant
            webp = _to_webp(clean)
            if webp in image_map:
                return image_map[webp]
            # 3. with extra images/ prefix (handles double images/images/ paths)
            with_prefix = f"images/{clean}"
            if with_prefix in image_map:
                return image_map[with_prefix]
            webp2 = _to_webp(with_prefix)
            if webp2 in image_map:
                return image_map[webp2]
            # 4. without images/ prefix (if path starts with images/)
            if clean.startswith("images/"):
                no_prefix = clean[len("images/"):]
                if no_prefix in image_map:
                    return image_map[no_prefix]
                webp3 = _to_webp(no_prefix)
                if webp3 in image_map:
                    return image_map[webp3]
            return None

        # Covers — ДО body rewrite, бо після rewrite body вже не містить fpsu.org.ua
        if not skip_covers:
            self._update_covers(_lookup, batch, dry_run)

        if not skip_body:
            self._rewrite_bodies(_lookup, batch, dry_run)

        if gallery:
            self._update_gallery(_lookup, batch, dry_run)

        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.flush()
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
            self.stdout.flush()

    def _rewrite_bodies(self, _lookup, batch: int, dry_run: bool) -> None:
        _write_out(self, "Rewriting Article.body …")
        arts_updated = self._rewrite_model(Article, "body", _lookup, batch, dry_run)
        _write_out(self, f"  → {arts_updated} articles rewritten")

        _write_out(self, "Rewriting StaticPage.body …")
        pages_updated = self._rewrite_model(StaticPage, "body", _lookup, batch, dry_run)
        _write_out(self, f"  → {pages_updated} pages rewritten")

    def _rewrite_model(self, model, field: str, _lookup, batch: int, dry_run: bool) -> int:
        """Обхід по pk (без OFFSET) + only(id, field) — швидше на PostgreSQL/Render."""
        base_qs = (
            model.objects.exclude(**{field: ""})
            .filter(**{f"{field}__icontains": "fpsu.org.ua/images/"})
            .order_by("pk")
            .only("id", field)
        )

        _write_out(
            self,
            f"  {model.__name__}: сканування батчами по pk (без COUNT — одразу йде робота) …",
        )

        last_pk = 0
        updated = 0
        scanned = 0

        while True:
            chunk = list(base_qs.filter(pk__gt=last_pk)[:batch])
            if not chunk:
                break
            last_pk = chunk[-1].pk
            scanned += len(chunk)

            to_save = []
            for obj in chunk:
                old_val = getattr(obj, field)
                new_val = self._replace_srcs(old_val, _lookup)
                if new_val != old_val:
                    setattr(obj, field, new_val)
                    to_save.append(obj)

            if to_save and not dry_run:
                with transaction.atomic():
                    model.objects.bulk_update(to_save, [field], batch_size=batch)
            updated += len(to_save)

            _write_out(
                self,
                f"    … pk≤{last_pk}, оброблено {scanned}, переписано: {updated}",
            )

        return updated

    def _replace_srcs(self, html: str, _lookup) -> str:
        def _sub(m: re.Match[str]) -> str:
            attr = m.group(1)
            orig_path = _path_from_match(m)
            cdn = _lookup(orig_path)
            if cdn:
                return f'{attr}="{cdn}"'
            return m.group(0)

        return _FPSU_RE.sub(_sub, html)

    def _update_covers(self, _lookup, batch: int, dry_run: bool) -> None:
        _write_out(self, "Updating Article.image (cover) …")

        base_qs = (
            Article.objects.filter(
                Q(image__isnull=True) | Q(image=""),
                body__icontains="fpsu.org.ua/images/",
            )
            .order_by("pk")
            .only("id", "body", "image")
        )

        _write_out(self, "  Covers: сканування батчами по pk (без COUNT) …")

        updated = 0
        last_pk = 0
        scanned = 0

        while True:
            chunk = list(base_qs.filter(pk__gt=last_pk)[:batch])
            if not chunk:
                break
            last_pk = chunk[-1].pk
            scanned += len(chunk)

            to_save = []
            for art in chunk:
                cdn_url = self._extract_cover_cdn(art.body, _lookup)
                if cdn_url:
                    art.image = cdn_url
                    to_save.append(art)

            if to_save and not dry_run:
                with transaction.atomic():
                    Article.objects.bulk_update(to_save, ["image"], batch_size=batch)
            updated += len(to_save)

            _write_out(
                self,
                f"    … pk≤{last_pk}, оброблено {scanned}, covers: {updated}",
            )

        _write_out(self, f"  → {updated} article covers set")

    def _extract_cover_cdn(self, body: str, _lookup) -> str | None:
        m = _FPSU_RE.search(body)
        if not m:
            return None
        orig_path = _path_from_match(m)
        return _lookup(orig_path)

    def _update_gallery(self, _lookup, batch: int, dry_run: bool) -> None:
        """Set GalleryAlbum.cover_image and GalleryPhoto.image from image_map."""
        from django.db.models import Q as _Q

        # #region agent log — debug gallery
        total_albums = GalleryAlbum.objects.count()
        null_cover = GalleryAlbum.objects.filter(_Q(cover_image__isnull=True) | _Q(cover_image="")).count()
        sample_albums = list(GalleryAlbum.objects.only("id", "cover_image", "cover_local")[:3])
        print(f"[DBG:gallery] albums total={total_albums} null_or_empty_cover={null_cover}", flush=True)
        for a in sample_albums:
            sample_cdn = _lookup(a.cover_local) if a.cover_local else None
            print(f"[DBG:gallery]   album pk={a.pk} cover_image={repr(str(a.cover_image))} cover_local={repr(a.cover_local)} lookup={sample_cdn}", flush=True)
        total_photos = GalleryPhoto.objects.count()
        null_img = GalleryPhoto.objects.filter(_Q(image__isnull=True) | _Q(image="")).count()
        sample_photos = list(GalleryPhoto.objects.only("id", "image", "image_local")[:3])
        print(f"[DBG:gallery] photos total={total_photos} null_or_empty_image={null_img}", flush=True)
        for p in sample_photos:
            sample_cdn = _lookup(p.image_local) if p.image_local else None
            print(f"[DBG:gallery]   photo pk={p.pk} image={repr(str(p.image))} image_local={repr(p.image_local)} lookup={sample_cdn}", flush=True)
        # #endregion

        _write_out(self, "Updating Gallery covers …")
        albums_updated = 0
        for album in GalleryAlbum.objects.filter(
            _Q(cover_image__isnull=True) | _Q(cover_image="")
        ).only("id", "cover_local"):
            if not album.cover_local:
                continue
            cdn = _lookup(album.cover_local)
            if cdn:
                if not dry_run:
                    GalleryAlbum.objects.filter(pk=album.pk).update(cover_image=cdn)
                albums_updated += 1
        _write_out(self, f"  → {albums_updated} album covers set")

        _write_out(self, "Updating Gallery photo images …")
        photos_updated = 0
        last_pk = 0
        while True:
            chunk = list(
                GalleryPhoto.objects.filter(
                    _Q(image__isnull=True) | _Q(image=""), pk__gt=last_pk
                )
                .order_by("pk")
                .only("id", "image_local")[:batch]
            )
            if not chunk:
                break
            last_pk = chunk[-1].pk
            to_save = []
            for photo in chunk:
                if not photo.image_local:
                    continue
                cdn = _lookup(photo.image_local)
                if cdn:
                    photo.image = cdn
                    to_save.append(photo)
            if to_save and not dry_run:
                with transaction.atomic():
                    GalleryPhoto.objects.bulk_update(to_save, ["image"], batch_size=batch)
            photos_updated += len(to_save)
        _write_out(self, f"  → {photos_updated} photo images set")
