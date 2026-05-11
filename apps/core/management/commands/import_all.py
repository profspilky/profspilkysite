"""
Management command: run the full Joomla → Django data import pipeline.

Orchestrates all individual import commands in the correct dependency order.
Idempotent: safe to re-run; each sub-command uses update_or_create / bulk_update
logic that skips already-imported records.

Pipeline steps
──────────────
  1. import_joomla           Category + Article records (metadata, no body)
  2. import_bodies           Article.body from content_bodies.json
  3. import_missing_articles Articles in dump but absent from the DB
  4. import_pages            StaticPage records from menu.tsv
  5. import_bodies --pages   StaticPage.body for menu→article pages
  6. seed_section_pages      Navigation section pages with hand-crafted HTML
  7. import_gallery          GalleryAlbum + GalleryPhoto

Flags
─────
  --dry-run           Pass to every sub-command; no DB writes anywhere.
  --skip-articles     Skip steps 1–3 (useful when articles are already imported).
  --skip-pages        Skip steps 4–6 (useful when only articles need refreshing).
  --skip-gallery      Skip step 7.
  --no-rewrite-images Disable /images/ → fpsu.org.ua rewriting in bodies
                      (steps 2, 3, 5). Default: rewriting is ON.

Usage
─────
  python manage.py import_all
  python manage.py import_all --dry-run
  python manage.py import_all --skip-articles
  python manage.py import_all --skip-gallery --dry-run
"""
from __future__ import annotations

import time
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the full Joomla → Django import pipeline in the correct order"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Pass --dry-run to every sub-command; no DB writes.",
        )
        parser.add_argument(
            "--skip-articles",
            action="store_true",
            help="Skip steps 1–3 (import_joomla, import_bodies, import_missing_articles).",
        )
        parser.add_argument(
            "--skip-pages",
            action="store_true",
            help="Skip steps 4–6 (import_pages, import_bodies --pages, seed_section_pages).",
        )
        parser.add_argument(
            "--skip-gallery",
            action="store_true",
            help="Skip step 7 (import_gallery).",
        )
        parser.add_argument(
            "--no-rewrite-images",
            action="store_true",
            help="Disable /images/ → https://www.fpsu.org.ua/images/ rewriting.",
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _section(self, label: str) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"{'─' * 60}"))
        self.stdout.write(self.style.MIGRATE_HEADING(f"  {label}"))
        self.stdout.write(self.style.MIGRATE_HEADING(f"{'─' * 60}"))

    def _run(self, name: str, **kwargs: Any) -> float:
        """Call a management command and return elapsed seconds."""
        self.stdout.write(self.style.SQL_KEYWORD(f"  → {name}") + f"  {kwargs}")
        t0 = time.monotonic()
        call_command(name, **kwargs)
        elapsed = time.monotonic() - t0
        self.stdout.write(self.style.SUCCESS(f"  ✓ {name} finished in {elapsed:.1f}s"))
        return elapsed

    # ── main ──────────────────────────────────────────────────────────────────

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        skip_articles: bool = options["skip_articles"]
        skip_pages: bool = options["skip_pages"]
        skip_gallery: bool = options["skip_gallery"]
        rewrite: bool = not options["no_rewrite_images"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved."))

        total_start = time.monotonic()

        # ── Steps 1–3: Articles ───────────────────────────────────────────────
        if skip_articles:
            self.stdout.write("Skipping article import steps (--skip-articles).")
        else:
            self._section("Step 1 — import categories + articles (metadata)")
            self._run("import_joomla", dry_run=dry_run)

            self._section("Step 2 — fill Article.body from content_bodies.json")
            self._run("import_bodies", rewrite_images=rewrite, dry_run=dry_run)

            self._section("Step 3 — import articles missing from DB")
            self._run("import_missing_articles", rewrite_images=rewrite, dry_run=dry_run)

        # ── Steps 4–6: Pages ─────────────────────────────────────────────────
        if skip_pages:
            self.stdout.write("Skipping page import steps (--skip-pages).")
        else:
            self._section("Step 4 — create StaticPage records from menu.tsv")
            self._run("import_pages", dry_run=dry_run)

            self._section("Step 5 — fill StaticPage.body for menu → article pages")
            self._run("import_bodies", pages=True, rewrite_images=rewrite, dry_run=dry_run)

            self._section("Step 6 — seed section/navigation pages with HTML content")
            self._run("seed_section_pages", dry_run=dry_run)

        # ── Step 7: Gallery ───────────────────────────────────────────────────
        if skip_gallery:
            self.stdout.write("Skipping gallery import (--skip-gallery).")
        else:
            self._section("Step 7 — import gallery albums + photos")
            self._run("import_gallery", dry_run=dry_run)

        # ── Summary ───────────────────────────────────────────────────────────
        total = time.monotonic() - total_start
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Pipeline complete in {total:.1f}s.")
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes were saved."))
