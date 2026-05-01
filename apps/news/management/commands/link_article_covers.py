"""
Management command: fill Article.local_image with the WebP path of the
cover image extracted from tools/articles.tsv (images JSON field).

Converts the original extension to .webp and verifies the file exists
in media/joomla_images/ before saving.

Usage:
    python manage.py link_article_covers
    python manage.py link_article_covers --skip-missing
    python manage.py link_article_covers --dry-run
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.news.models import Article

BASE = Path(__file__).resolve().parents[4]
DEFAULT_ARTS = BASE / "tools" / "articles.tsv"
MEDIA_DIR = BASE / "media" / "joomla_images"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"}


def _to_webp(path_str: str) -> str:
    p = Path(path_str.lstrip("/"))
    if p.suffix.lower() == ".webp":
        return str(p)
    return str(p.with_suffix(".webp"))


def _extract_cover(images_json: str) -> str:
    if not images_json or images_json in ("NULL", ""):
        return ""
    try:
        data = json.loads(images_json)
    except Exception:
        return ""
    for field in ("image_intro", "image_fulltext"):
        val = (data.get(field) or "").strip().lstrip("/")
        if val:
            return val
    return ""


class Command(BaseCommand):
    help = "Fill Article.local_image with local WebP cover paths from articles.tsv"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--arts-tsv", default=str(DEFAULT_ARTS))
        parser.add_argument(
            "--skip-missing",
            action="store_true",
            help="Skip articles whose WebP file doesn't exist locally",
        )
        parser.add_argument("--batch", type=int, default=500)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        arts_path = Path(options["arts_tsv"])
        skip_missing: bool = options["skip_missing"]
        batch: int = options["batch"]
        dry_run: bool = options["dry_run"]

        # Build joomla_id → webp_path map
        cover_map: dict[int, str] = {}
        for line in arts_path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split("\t")
            if len(parts) < 8:
                continue
            jid = parts[0]
            if not jid or jid == "NULL":
                continue
            images_json = parts[6]
            cover = _extract_cover(images_json)
            if not cover:
                continue
            webp = _to_webp(cover)
            local_path = MEDIA_DIR / webp
            if skip_missing and not local_path.exists():
                continue
            cover_map[int(jid)] = webp

        self.stdout.write(f"Articles with cover images: {len(cover_map)}")

        # Fetch matching articles that don't yet have local_image set
        jids = list(cover_map.keys())
        articles = Article.objects.filter(
            joomla_id__in=jids, local_image=""
        )
        self.stdout.write(f"Articles to update: {articles.count()}")

        updated = 0
        to_save: list[Article] = []

        for art in articles.iterator(chunk_size=batch):
            path = cover_map.get(art.joomla_id or 0)
            if not path:
                continue
            art.local_image = path
            to_save.append(art)

            if len(to_save) >= batch:
                if not dry_run:
                    with transaction.atomic():
                        Article.objects.bulk_update(to_save, ["local_image"], batch_size=batch)
                updated += len(to_save)
                to_save = []
                self.stdout.write(f"  … {updated} updated")

        if to_save:
            if not dry_run:
                with transaction.atomic():
                    Article.objects.bulk_update(to_save, ["local_image"], batch_size=batch)
            updated += len(to_save)

        self.stdout.write(self.style.SUCCESS(f"Done. {updated} articles updated."))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
