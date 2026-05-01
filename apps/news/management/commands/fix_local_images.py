"""
Management command: rewrite image paths in Article.body and StaticPage.body.

  Before: src="images/foo/bar.jpg"   or  src="/images/foo/bar.jpg"
  After:  src="/media/joomla_images/images/foo/bar.webp"

Also rewrites href= attributes that point into the images tree.

Usage:
    python manage.py fix_local_images
    python manage.py fix_local_images --batch 500 --dry-run
"""
from __future__ import annotations

import re
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.news.models import Article
from apps.pages.models import StaticPage

# Matches src or href pointing at images/... (with or without leading slash)
# Group 1: attribute name (src|href)
# Group 2: optional leading slash
# Group 3: path inside images/ (without extension)
# Group 4: original extension
_IMG_RE = re.compile(
    r'(src|href)="/?images/([^"]+?)\.(jpe?g|png|gif|bmp|tiff?)"',
    re.IGNORECASE,
)
_MEDIA_PREFIX = "/media/joomla_images/images/"


def _rewrite(html: str) -> str:
    def _replace(m: re.Match) -> str:
        attr = m.group(1)
        inner = m.group(2)
        return f'{attr}="{_MEDIA_PREFIX}{inner}.webp"'
    return _IMG_RE.sub(_replace, html)


class Command(BaseCommand):
    help = "Rewrite image src/href in Article.body and StaticPage.body to use local WebP files"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch", type=int, default=500)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        batch: int = options["batch"]
        dry_run: bool = options["dry_run"]

        total_articles = self._fix_model(Article, "body", batch, dry_run)
        total_pages = self._fix_model(StaticPage, "body", batch, dry_run)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Articles updated: {total_articles}, "
                f"StaticPages updated: {total_pages}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))

    def _fix_model(self, model, field: str, batch: int, dry_run: bool) -> int:
        qs = model.objects.exclude(**{field: ""})
        total = qs.count()
        self.stdout.write(f"{model.__name__}: {total} records with content …")

        updated = 0
        offset = 0
        while True:
            chunk = list(qs[offset: offset + batch])
            if not chunk:
                break
            offset += batch

            to_save = []
            for obj in chunk:
                old = getattr(obj, field)
                new = _rewrite(old)
                if new != old:
                    setattr(obj, field, new)
                    to_save.append(obj)

            if to_save and not dry_run:
                with transaction.atomic():
                    model.objects.bulk_update(to_save, [field], batch_size=batch)
            updated += len(to_save)

        self.stdout.write(f"  → {updated} records rewritten")
        return updated
