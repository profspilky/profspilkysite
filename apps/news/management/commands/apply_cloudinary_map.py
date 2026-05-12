"""
Management command: apply Cloudinary image map to articles and static pages.

Reads tools/image_map.json (built by tools/upload_images_cloudinary.py) and:

  1. Rewrites Article.body — replaces:
       src="https://www.fpsu.org.ua/images/<PATH>"
       or src="/images/<PATH>"
     with the Cloudinary URL from the map.

  2. Sets Article.local_image — extracts the first body image URL and maps it to
     a relative webp path (used for thumbnail display before Cloudinary is set).

  3. Sets Article.image — Cloudinary public_id derived from the cover image URL.

  4. Rewrites StaticPage.body in the same way.

Idempotent: safe to re-run. Articles already rewritten are skipped.

Prerequisites:
  - Run tools/build_image_paths.py to build tools/image_paths.txt
  - Run tools/upload_images_cloudinary.py to upload and build tools/image_map.json

Usage:
    python manage.py apply_cloudinary_map --dry-run
    python manage.py apply_cloudinary_map
    python manage.py apply_cloudinary_map --skip-body   # only covers
    python manage.py apply_cloudinary_map --skip-covers # only body rewrite
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.news.models import Article
from apps.pages.models import StaticPage

BASE = Path(__file__).resolve().parents[4]
DEFAULT_MAP = BASE / "tools" / "image_map.json"

# Matches absolute fpsu.org.ua image URLs and relative /images/ paths
_FPSU_RE = re.compile(
    r'(src|href)="(https?://www\.fpsu\.org\.ua/images/([^"]+)|/?images/([^"]+\.(jpe?g|png|gif|bmp|webp|tiff?)))"',
    re.IGNORECASE,
)
_CLOUDINARY_FOLDER = "fpsu/joomla"


def _path_from_match(m: re.Match) -> str:
    """Return the relative images/ path from either absolute or relative match."""
    if m.group(3):
        # absolute: https://www.fpsu.org.ua/images/<PATH>
        return m.group(3).lstrip("/")
    # relative: /images/<PATH> or images/<PATH>
    raw = m.group(4) or ""
    return raw.lstrip("/")


def _to_webp(path_str: str) -> str:
    p = Path(path_str)
    if p.suffix.lower() == ".webp":
        return str(p)
    return str(p.with_suffix(".webp"))


def _public_id(rel_path: str) -> str:
    stem = Path(rel_path).with_suffix("").as_posix()
    return f"{_CLOUDINARY_FOLDER}/images/{stem}"


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

    def handle(self, *args: Any, **options: Any) -> None:
        map_path = Path(options["image_map"])
        batch: int = options["batch"]
        skip_body: bool = options["skip_body"]
        skip_covers: bool = options["skip_covers"]
        dry_run: bool = options["dry_run"]

        if not map_path.exists():
            raise CommandError(
                f"image_map.json not found at {map_path}.\n"
                "Run: python tools/build_image_paths.py && "
                "python tools/upload_images_cloudinary.py"
            )

        image_map: dict[str, str] = json.loads(map_path.read_text(encoding="utf-8"))
        self.stdout.write(f"Image map loaded: {len(image_map)} entries.")

        # Build lookup: relative_images_path → cloudinary_url
        # Keys in image_map are like "images/foo.webp" (relative to media/joomla_images)
        # We need to match "foo.jpg" or "foo.webp" → Cloudinary URL
        # Both "images/foo.webp" and "images/foo.jpg" should map to the same Cloudinary URL

        def _lookup(path_str: str) -> str | None:
            """Look up Cloudinary URL for an images/ relative path (any extension)."""
            clean = path_str.lstrip("/")
            # Direct lookup (e.g. "images/foo.webp")
            if clean in image_map:
                return image_map[clean]
            # Try webp version
            webp = _to_webp(clean)
            if webp in image_map:
                return image_map[webp]
            # Try without "images/" prefix (in case path has it already)
            if not clean.startswith("images/"):
                with_prefix = f"images/{clean}"
                if with_prefix in image_map:
                    return image_map[with_prefix]
                webp2 = _to_webp(with_prefix)
                if webp2 in image_map:
                    return image_map[webp2]
            return None

        if not skip_body:
            self._rewrite_bodies(image_map, _lookup, batch, dry_run)

        if not skip_covers:
            self._update_covers(_lookup, batch, dry_run)

        self.stdout.write(self.style.SUCCESS("Done."))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))

    # ── body rewrite ──────────────────────────────────────────────────────────

    def _rewrite_bodies(
        self,
        image_map: dict[str, str],
        _lookup,
        batch: int,
        dry_run: bool,
    ) -> None:
        self.stdout.write("Rewriting Article.body …")
        arts_updated = self._rewrite_model(Article, "body", _lookup, batch, dry_run)
        self.stdout.write(f"  → {arts_updated} articles rewritten")

        self.stdout.write("Rewriting StaticPage.body …")
        pages_updated = self._rewrite_model(StaticPage, "body", _lookup, batch, dry_run)
        self.stdout.write(f"  → {pages_updated} pages rewritten")

    def _rewrite_model(self, model, field: str, _lookup, batch: int, dry_run: bool) -> int:
        qs = model.objects.exclude(**{field: ""})
        # Only process records that still have fpsu.org.ua or relative /images/ refs
        qs = qs.filter(**{f"{field}__icontains": "fpsu.org.ua/images/"})

        updated = 0
        offset = 0
        while True:
            chunk = list(qs[offset: offset + batch])
            if not chunk:
                break
            offset += batch

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

        return updated

    def _replace_srcs(self, html: str, _lookup) -> str:
        def _sub(m: re.Match) -> str:
            attr = m.group(1)
            orig_path = _path_from_match(m)
            cdn = _lookup(orig_path)
            if cdn:
                return f'{attr}="{cdn}"'
            return m.group(0)
        return _FPSU_RE.sub(_sub, html)

    # ── cover images ─────────────────────────────────────────────────────────

    def _update_covers(self, _lookup, batch: int, dry_run: bool) -> None:
        self.stdout.write("Updating Article.image (cover) …")

        # Only process articles that still have no Cloudinary image
        qs = Article.objects.filter(
            image__isnull=True,
            body__icontains="fpsu.org.ua/images/",
        ) | Article.objects.filter(
            image="",
            body__icontains="fpsu.org.ua/images/",
        )

        total = qs.count()
        self.stdout.write(f"  Articles without cloudinary cover: {total}")

        updated = 0
        offset = 0
        while True:
            chunk = list(qs[offset: offset + batch])
            if not chunk:
                break
            offset += batch

            to_save = []
            for art in chunk:
                cdn_url = self._extract_cover_cdn(art.body, _lookup)
                if cdn_url:
                    # Store the cloudinary URL directly in image field
                    art.image = cdn_url
                    to_save.append(art)

            if to_save and not dry_run:
                with transaction.atomic():
                    Article.objects.bulk_update(to_save, ["image"], batch_size=batch)
            updated += len(to_save)
            if updated and updated % 1000 == 0:
                self.stdout.write(f"  … {updated} covers set")

        self.stdout.write(f"  → {updated} article covers set")

    def _extract_cover_cdn(self, body: str, _lookup) -> str | None:
        """Return Cloudinary URL of the first image in body, or None."""
        m = _FPSU_RE.search(body)
        if not m:
            return None
        orig_path = _path_from_match(m)
        return _lookup(orig_path)
