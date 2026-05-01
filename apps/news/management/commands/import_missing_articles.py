"""
Management command: import articles present in content_bodies.json
but absent from the Django Article table.

Reads tools/content_bodies.json (produced by tools/parse_bodies.py),
filters to state=1 (published), finds IDs not yet in the DB, and
bulk-creates them with full body content.

Usage:
    python manage.py import_missing_articles
    python manage.py import_missing_articles --rewrite-images
    python manage.py import_missing_articles --all-states
    python manage.py import_missing_articles --dry-run

Options:
    --bodies-json   Path to content_bodies.json (default: tools/content_bodies.json)
    --rewrite-images
                    Rewrite /images/ → https://www.fpsu.org.ua/images/ in body.
    --all-states    Import articles with any state value, not just state=1.
    --batch         bulk_create batch size (default 200).
    --dry-run       Print stats without saving.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from django.utils.text import slugify

from apps.news.models import Article, Category

BASE = Path(__file__).resolve().parents[4]
DEFAULT_BODIES = BASE / "tools" / "content_bodies.json"

_IMAGE_SRC_RE = re.compile(r'(src|href)="(/?images/)', re.IGNORECASE)
_FPSU_BASE = "https://www.fpsu.org.ua"


def _rewrite_images(html: str) -> str:
    """Prepend fpsu.org.ua to relative image paths (both /images/ and images/)."""
    return _IMAGE_SRC_RE.sub(rf'\1="{_FPSU_BASE}/images/', html)


def _safe_date(raw: str):
    if not raw or raw in ("NULL", "0000-00-00", "0000-00-00 00:00:00"):
        return None
    try:
        dt = parse_datetime(raw + " 00:00:00") if len(raw) == 10 else parse_datetime(raw)
        if dt is None:
            return None
        return dt if dt.tzinfo is not None else make_aware(dt)
    except Exception:
        return None


def _unique_slug(base_slug: str, existing_slugs: set[str]) -> str:
    """Return a unique slug not present in existing_slugs; adds it once found."""
    slug = base_slug[:400]
    if slug not in existing_slugs:
        existing_slugs.add(slug)
        return slug
    i = 2
    while True:
        candidate = f"{base_slug[:390]}-{i}"
        if candidate not in existing_slugs:
            existing_slugs.add(candidate)
            return candidate
        i += 1


class Command(BaseCommand):
    help = "Import published articles missing from the DB (state=1 in dump but absent in Article table)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--bodies-json", default=str(DEFAULT_BODIES))
        parser.add_argument(
            "--rewrite-images",
            action="store_true",
            help="Rewrite /images/ → https://www.fpsu.org.ua/images/ in body HTML",
        )
        parser.add_argument(
            "--all-states",
            action="store_true",
            help="Import articles of any state, not just published (state=1)",
        )
        parser.add_argument("--batch", type=int, default=200)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        bodies_path = Path(options["bodies_json"])
        rewrite: bool = options["rewrite_images"]
        all_states: bool = options["all_states"]
        batch: int = options["batch"]
        dry_run: bool = options["dry_run"]

        if not bodies_path.exists():
            raise CommandError(
                f"content_bodies.json not found: {bodies_path}\n"
                "Run `python tools/parse_bodies.py` first."
            )

        self.stdout.write(f"Loading {bodies_path} …")
        dump_rows: list[dict] = json.loads(bodies_path.read_text(encoding="utf-8"))

        if not all_states:
            dump_rows = [r for r in dump_rows if r.get("state") == 1]
        self.stdout.write(f"  {len(dump_rows)} rows in dump (after state filter).")

        # ── Existing joomla_ids in DB ─────────────────────────────────────────
        existing_jids: set[int] = set(
            Article.objects.filter(joomla_id__isnull=False).values_list(
                "joomla_id", flat=True
            )
        )
        self.stdout.write(f"  {len(existing_jids)} articles already in DB.")

        new_rows = [r for r in dump_rows if r["id"] not in existing_jids]
        self.stdout.write(
            self.style.SUCCESS(f"  {len(new_rows)} new articles to create.")
        )

        if not new_rows:
            self.stdout.write("Nothing to do.")
            return

        # ── Preload category map {joomla_id: Category} ────────────────────────
        cat_map: dict[int, Category] = {
            c.joomla_id: c
            for c in Category.objects.filter(joomla_id__isnull=False)
        }

        # ── Preload existing slugs to guarantee uniqueness ────────────────────
        existing_slugs: set[str] = set(
            Article.objects.values_list("slug", flat=True)
        )

        # ── Build Article objects ─────────────────────────────────────────────
        to_create: list[Article] = []
        for row in new_rows:
            intro: str = row.get("introtext") or ""
            full: str = row.get("fulltext") or ""
            body = intro + full
            if rewrite:
                body = _rewrite_images(body)

            alias = row.get("alias") or ""
            base_slug = alias[:400] if alias else f"article-{row['id']}"
            slug = _unique_slug(base_slug, existing_slugs)

            pub_dt = _safe_date(row.get("publish_up") or "")

            art = Article(
                joomla_id=row["id"],
                title=(row.get("title") or "")[:255],
                slug=slug,
                body=body,
                summary="",
                is_published=True,
                category=cat_map.get(row.get("catid") or 0),
            )
            if pub_dt:
                art.published_at = pub_dt

            to_create.append(art)

        self.stdout.write(f"Prepared {len(to_create)} Article objects.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
            return

        created_total = 0
        with transaction.atomic():
            for i in range(0, len(to_create), batch):
                chunk = to_create[i : i + batch]
                Article.objects.bulk_create(chunk, batch_size=batch)
                created_total += len(chunk)
                if created_total % 1000 == 0 or created_total == len(to_create):
                    self.stdout.write(f"  … {created_total}/{len(to_create)} created")

        self.stdout.write(
            self.style.SUCCESS(f"Done. {created_total} new articles created.")
        )
