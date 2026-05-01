"""
Management command: fill StaticPage.body for menu items that link to a
specific Joomla article (com_content&view=article&id=XXX).

Reads:
  tools/menu.tsv          – to map StaticPage.joomla_id → article ID
  tools/content_bodies.json – article body content

Usage:
    python manage.py fill_page_bodies
    python manage.py fill_page_bodies --dry-run
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.pages.models import StaticPage

BASE = Path(__file__).resolve().parents[4]
DEFAULT_MENU = BASE / "tools" / "menu.tsv"
DEFAULT_BODIES = BASE / "tools" / "content_bodies.json"
MEDIA_PREFIX = "/media/joomla_images/images/"

_ARTICLE_ID_RE = re.compile(r"view=article&(?:amp;)?id=(\d+)", re.IGNORECASE)
_IMG_RE = re.compile(
    r'(src|href)="/?images/([^"]+?)\.(jpe?g|png|gif|bmp|tiff?)"',
    re.IGNORECASE,
)


def _rewrite_img(html: str) -> str:
    def _r(m: re.Match) -> str:
        return f'{m.group(1)}="{MEDIA_PREFIX}{m.group(2)}.webp"'
    return _IMG_RE.sub(_r, html)


class Command(BaseCommand):
    help = "Fill StaticPage.body from content_bodies.json for menu→article pages"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--menu-tsv", default=str(DEFAULT_MENU))
        parser.add_argument("--bodies-json", default=str(DEFAULT_BODIES))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        menu_path = Path(options["menu_tsv"])
        bodies_path = Path(options["bodies_json"])

        # Build menu_id → article_id map
        menu_to_article: dict[int, int] = {}
        for line in menu_path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            mid, title, alias, path, link, mtype, parent_id = parts[:7]
            if not mid.isdigit():
                continue
            m = _ARTICLE_ID_RE.search(link)
            if m:
                menu_to_article[int(mid)] = int(m.group(1))

        self.stdout.write(f"Menu items linking to articles: {len(menu_to_article)}")

        # Load article bodies
        bodies_by_id: dict[int, dict] = {
            row["id"]: row
            for row in json.loads(bodies_path.read_text(encoding="utf-8"))
        }

        # Find StaticPages that need body from article
        updated = 0
        skipped_no_body = 0

        pages = StaticPage.objects.filter(joomla_id__in=list(menu_to_article.keys()))
        self.stdout.write(f"StaticPages matched: {pages.count()}")

        to_save = []
        for page in pages:
            if page.body:
                continue
            article_id = menu_to_article.get(page.joomla_id)
            if not article_id:
                continue
            row = bodies_by_id.get(article_id)
            if not row:
                skipped_no_body += 1
                continue
            body = (row.get("introtext") or "") + (row.get("fulltext") or "")
            body = _rewrite_img(body)
            page.body = body
            to_save.append(page)

        if to_save and not dry_run:
            with transaction.atomic():
                StaticPage.objects.bulk_update(to_save, ["body"])
            updated = len(to_save)
        elif dry_run:
            updated = len(to_save)

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated: {updated} pages, "
                f"skipped (no body in dump): {skipped_no_body}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
