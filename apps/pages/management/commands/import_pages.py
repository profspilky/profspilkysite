"""
Management command: import Joomla menu items as StaticPage records.

Reads tools/menu.tsv and creates or updates StaticPage rows so that
the original Joomla menu URLs are served by Django.

Also imports root-level Joomla articles (no category path) as StaticPage
when they are NOT already in the Article table — these appear as standalone
pages at /<id>-<alias>.html.

Usage:
    python manage.py import_pages
    python manage.py import_pages --dry-run
    python manage.py import_pages --menu-tsv tools/menu.tsv
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.pages.models import StaticPage

BASE = Path(__file__).resolve().parents[4]
DEFAULT_MENU = BASE / "tools" / "menu.tsv"


def _read_tsv(path: Path, num_cols: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) < num_cols:
            continue
        if len(parts) > num_cols:
            parts = parts[: num_cols - 1] + ["\t".join(parts[num_cols - 1 :])]
        rows.append(parts)
    return rows


class Command(BaseCommand):
    help = "Import Joomla menu items as StaticPage records"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--menu-tsv", default=str(DEFAULT_MENU))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        menu_path = Path(options["menu_tsv"])
        dry_run: bool = options["dry_run"]

        if not menu_path.exists():
            raise CommandError(f"File not found: {menu_path}")

        created_count = updated_count = skipped = 0

        with transaction.atomic():
            for row in _read_tsv(menu_path, 7):
                mid, title, alias, path, link, mtype, parent_id = row

                if not path or path in ("NULL", ""):
                    skipped += 1
                    continue

                # Determine stored url_path
                # For Joomla SEF URLs: path = "pro-fpu/istoriya-fpu" → /pro-fpu/istoriya-fpu
                # We store both plain and .html variants so both URL patterns match
                url_path = f"/{path}"

                defaults = {
                    "title": title[:255],
                    "is_published": True,
                    "joomla_id": int(mid) if mid.isdigit() else None,
                    "joomla_type": "menu",
                }

                if not dry_run:
                    _, created = StaticPage.objects.update_or_create(
                        url_path=url_path,
                        defaults=defaults,
                    )
                    # Also create the .html variant pointing to the same content
                    url_path_html = f"/{path}.html"
                    StaticPage.objects.get_or_create(
                        url_path=url_path_html,
                        defaults={**defaults, "title": title[:255]},
                    )
                else:
                    created = True

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Pages: {created_count} created, {updated_count} updated, "
                f"{skipped} skipped (no path)"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
