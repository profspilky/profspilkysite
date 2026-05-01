"""
Management command: fill Article.body and StaticPage.body from content_bodies.json.

Article.body  = introtext + fulltext (for every Article whose joomla_id matches).
StaticPage.body = body of the article linked via Joomla menu (when --pages is set
                  and the menu link contains view=article&id=NNN).

Usage:
    python manage.py import_bodies
    python manage.py import_bodies --rewrite-images
    python manage.py import_bodies --pages
    python manage.py import_bodies --rewrite-images --pages --dry-run

Options:
    --bodies-json   Path to content_bodies.json  (default: tools/content_bodies.json)
    --menu-tsv      Path to menu.tsv             (default: tools/menu.tsv)
    --rewrite-images
                    Replace src="/images/ → src="https://www.fpsu.org.ua/images/
                    and href="/images/ → href="https://www.fpsu.org.ua/images/
                    in body HTML so inline images render without local files.
    --pages         Also update StaticPage.body for menu items that link to a
                    single article (view=article&id=NNN).
    --batch         Bulk-update batch size (default 500).
    --dry-run       Print stats without saving.
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
DEFAULT_BODIES = BASE / "tools" / "content_bodies.json"
DEFAULT_MENU = BASE / "tools" / "menu.tsv"

_IMAGE_SRC_RE = re.compile(r'(src|href)="(/?images/)', re.IGNORECASE)
_ARTICLE_ID_RE = re.compile(r"view=article&(?:amp;)?id=(\d+)", re.IGNORECASE)
_FPSU_BASE = "https://www.fpsu.org.ua"


def _rewrite_images(html: str) -> str:
    """Prepend fpsu.org.ua to relative image paths (both /images/ and images/)."""
    return _IMAGE_SRC_RE.sub(rf'\1="{_FPSU_BASE}/images/', html)


def _read_menu_tsv(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        if len(parts) > 7:
            parts = parts[:6] + ["\t".join(parts[6:])]
        rows.append(parts)
    return rows


class Command(BaseCommand):
    help = "Populate Article.body and (optionally) StaticPage.body from content_bodies.json"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--bodies-json", default=str(DEFAULT_BODIES))
        parser.add_argument("--menu-tsv", default=str(DEFAULT_MENU))
        parser.add_argument(
            "--rewrite-images",
            action="store_true",
            help="Rewrite /images/ → https://www.fpsu.org.ua/images/ in body HTML",
        )
        parser.add_argument(
            "--pages",
            action="store_true",
            help="Also populate StaticPage.body for single-article menu links",
        )
        parser.add_argument("--batch", type=int, default=500)
        parser.add_argument("--dry-run", action="store_true")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_body_map(self, bodies_path: Path) -> dict[int, dict]:
        """Return {joomla_id: row} for all rows in content_bodies.json."""
        self.stdout.write(f"Loading {bodies_path} …")
        data: list[dict] = json.loads(bodies_path.read_text(encoding="utf-8"))
        body_map = {row["id"]: row for row in data}
        self.stdout.write(f"  {len(body_map)} records loaded.")
        return body_map

    def _build_body(self, row: dict, rewrite: bool) -> str:
        intro: str = row.get("introtext") or ""
        full: str = row.get("fulltext") or ""
        body = intro + full
        if rewrite:
            body = _rewrite_images(body)
        return body

    # ── Article update ────────────────────────────────────────────────────────

    def _update_articles(
        self,
        body_map: dict[int, dict],
        batch: int,
        rewrite: bool,
        dry_run: bool,
    ) -> None:
        self.stdout.write("Updating Article.body …")

        # Fetch all articles that have a joomla_id and an empty body
        qs = Article.objects.filter(
            joomla_id__isnull=False,
        ).only("id", "joomla_id", "body")

        to_update: list[Article] = []
        skipped = missing = 0

        for art in qs.iterator(chunk_size=2000):
            jid = art.joomla_id
            row = body_map.get(jid)
            if row is None:
                missing += 1
                continue
            new_body = self._build_body(row, rewrite)
            if art.body == new_body:
                skipped += 1
                continue
            art.body = new_body
            to_update.append(art)

        self.stdout.write(
            f"  Found:   {len(to_update)} to update, "
            f"{skipped} already up-to-date, {missing} not in dump."
        )

        if dry_run or not to_update:
            return

        updated_total = 0
        with transaction.atomic():
            for i in range(0, len(to_update), batch):
                chunk = to_update[i : i + batch]
                Article.objects.bulk_update(chunk, ["body"], batch_size=batch)
                updated_total += len(chunk)
                if updated_total % 5000 == 0 or updated_total == len(to_update):
                    self.stdout.write(f"  … {updated_total}/{len(to_update)} updated")

        self.stdout.write(
            self.style.SUCCESS(f"  Article.body: {updated_total} rows updated.")
        )

    # ── StaticPage update ─────────────────────────────────────────────────────

    def _update_pages(
        self,
        body_map: dict[int, dict],
        menu_path: Path,
        rewrite: bool,
        dry_run: bool,
    ) -> None:
        self.stdout.write("Updating StaticPage.body for single-article menu links …")

        if not menu_path.exists():
            self.stdout.write(
                self.style.WARNING(f"  menu.tsv not found: {menu_path} — skipping pages.")
            )
            return

        # Build: menu_item_joomla_id → article_joomla_id
        menu_to_article: dict[int, int] = {}
        for row in _read_menu_tsv(menu_path):
            mid, title, alias, path, link, mtype, parent_id = row
            if not link or link in ("NULL", ""):
                continue
            m = _ARTICLE_ID_RE.search(link)
            if m and mid.isdigit():
                menu_to_article[int(mid)] = int(m.group(1))

        self.stdout.write(
            f"  {len(menu_to_article)} menu items link to a single article."
        )

        pages_qs = StaticPage.objects.filter(
            joomla_type="menu", joomla_id__isnull=False
        ).only("id", "joomla_id", "body")

        to_update: list[StaticPage] = []
        skipped = missing = 0

        for page in pages_qs.iterator():
            art_jid = menu_to_article.get(page.joomla_id)
            if art_jid is None:
                missing += 1
                continue
            row = body_map.get(art_jid)
            if row is None:
                missing += 1
                continue
            new_body = self._build_body(row, rewrite)
            if page.body == new_body:
                skipped += 1
                continue
            page.body = new_body
            to_update.append(page)

        self.stdout.write(
            f"  {len(to_update)} pages to update, {skipped} up-to-date, "
            f"{missing} no matching article."
        )

        if dry_run or not to_update:
            return

        with transaction.atomic():
            StaticPage.objects.bulk_update(to_update, ["body"], batch_size=200)

        self.stdout.write(
            self.style.SUCCESS(f"  StaticPage.body: {len(to_update)} rows updated.")
        )

    # ── main ──────────────────────────────────────────────────────────────────

    def handle(self, *args: Any, **options: Any) -> None:
        bodies_path = Path(options["bodies_json"])
        menu_path = Path(options["menu_tsv"])
        rewrite: bool = options["rewrite_images"]
        do_pages: bool = options["pages"]
        batch: int = options["batch"]
        dry_run: bool = options["dry_run"]

        if not bodies_path.exists():
            raise CommandError(
                f"content_bodies.json not found: {bodies_path}\n"
                "Run `python tools/parse_bodies.py` first."
            )

        body_map = self._load_body_map(bodies_path)

        self._update_articles(body_map, batch, rewrite, dry_run)

        if do_pages:
            self._update_pages(body_map, menu_path, rewrite, dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
        else:
            self.stdout.write(self.style.SUCCESS("Done."))
