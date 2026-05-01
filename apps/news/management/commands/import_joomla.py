"""
Management command: import categories and articles from Joomla MySQL export.

Usage:
    python manage.py import_joomla
    python manage.py import_joomla --dry-run
    python manage.py import_joomla --cats-tsv tools/cats.tsv --arts-tsv tools/articles.tsv

Data sources:
    tools/cats.tsv     – tab-separated categories from zeki2_categories
    tools/articles.tsv – tab-separated articles from zeki2_content

The command is idempotent: re-running updates existing records via joomla_id.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

from apps.news.models import Article, Category


BASE = Path(__file__).resolve().parents[4]  # apps/news/management/commands → project root
DEFAULT_CATS = BASE / "tools" / "cats.tsv"
DEFAULT_ARTS = BASE / "tools" / "articles.tsv"

_IMG_FIELDS = ("image_intro", "image_fulltext")


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


def _extract_image_intro(images_json: str) -> str:
    if not images_json or images_json in ("NULL", ""):
        return ""
    try:
        data = json.loads(images_json)
    except json.JSONDecodeError:
        return ""
    for field in _IMG_FIELDS:
        val = data.get(field, "")
        if val and val.strip():
            return val.strip()
    return ""


def _safe_date(raw: str):
    if not raw or raw in ("NULL", "0000-00-00", "0000-00-00 00:00:00"):
        return None
    try:
        dt = parse_datetime(raw + " 00:00:00") if len(raw) == 10 else parse_datetime(raw)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = make_aware(dt)
        return dt
    except Exception:
        return None


class Command(BaseCommand):
    help = "Import Joomla categories and articles from TSV exports"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--cats-tsv", default=str(DEFAULT_CATS))
        parser.add_argument("--arts-tsv", default=str(DEFAULT_ARTS))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        cats_path = Path(options["cats_tsv"])
        arts_path = Path(options["arts_tsv"])
        dry_run: bool = options["dry_run"]

        for p in (cats_path, arts_path):
            if not p.exists():
                raise CommandError(f"File not found: {p}")

        # ── Import categories ─────────────────────────────────────────────────
        self.stdout.write("Importing categories…")
        cats_by_jid: dict[str, Category] = {}
        cat_created = cat_updated = 0

        rows = _read_tsv(cats_path, 6)
        for row in rows:
            cid, alias, title, path, metadesc, metakey = row
            if not cid or cid == "NULL":
                continue

            # Ensure alias uniqueness: append joomla_id if already taken by another row
            unique_alias = alias[:400]
            if not dry_run and Category.objects.filter(alias=unique_alias).exclude(
                joomla_id=int(cid)
            ).exists():
                unique_alias = f"{alias[:390]}-{cid}"

            defaults = {
                "alias": unique_alias,
                "title": title[:255],
                "path": path.strip("/")[:400],
                "meta_description": metadesc[:1024],
                "meta_keywords": metakey[:1024],
                "is_active": True,
            }

            if not dry_run:
                cat_obj, was_created = Category.objects.update_or_create(
                    joomla_id=int(cid),
                    defaults=defaults,
                )
            else:
                cat_obj = Category(joomla_id=int(cid), **defaults)
                was_created = True

            cats_by_jid[cid] = cat_obj
            if was_created:
                cat_created += 1
            else:
                cat_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  Categories: {cat_created} created, {cat_updated} updated"
            )
        )

        # ── Import articles ───────────────────────────────────────────────────
        self.stdout.write("Importing articles…")
        art_created = art_updated = art_skipped = 0

        rows = _read_tsv(arts_path, 8)
        with transaction.atomic():
            for row in rows:
                jid, alias, catid, title, metadesc, metakey, images_json, pub_date = row
                if not jid or jid == "NULL":
                    art_skipped += 1
                    continue

                category = cats_by_jid.get(catid)
                pub_dt = _safe_date(pub_date)
                image_path = _extract_image_intro(images_json)

                base_slug = alias[:400] if alias else f"article-{jid}"
                # Ensure slug uniqueness
                slug = base_slug
                if not dry_run and Article.objects.filter(slug=slug).exclude(
                    joomla_id=int(jid)
                ).exists():
                    slug = f"{base_slug[:390]}-{jid}"
                defaults: dict = {
                    "title": title[:255],
                    "slug": slug,
                    "category": category,
                    "meta_description": metadesc[:500],
                    "meta_keywords": metakey[:500],
                    "is_published": True,
                    "summary": "",
                    "body": "",
                }
                if pub_dt:
                    defaults["published_at"] = pub_dt

                was_created_art: bool
                if not dry_run:
                    _, was_created_art = Article.objects.update_or_create(
                        joomla_id=int(jid),
                        defaults=defaults,
                    )
                else:
                    was_created_art = True

                if was_created_art:
                    art_created += 1
                else:
                    art_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  Articles: {art_created} created, {art_updated} updated, "
                f"{art_skipped} skipped"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
