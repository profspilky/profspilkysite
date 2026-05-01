"""
Management command: download inline images from article bodies and re-upload
to Cloudinary, then rewrite the src URLs in body HTML.

Finds all unique image src attributes pointing to fpsu.org.ua or relative
/images/ paths inside Article.body and StaticPage.body, downloads each image,
uploads to Cloudinary, and replaces the original src with the Cloudinary URL.

Prerequisites:
    - Article.body populated (run import_bodies --rewrite-images first)
    - Cloudinary configured via CLOUDINARY_URL or individual ENV vars

Usage:
    python manage.py import_body_images --dry-run     # show stats only
    python manage.py import_body_images               # download + upload + rewrite
    python manage.py import_body_images --workers 4   # parallel downloads
    python manage.py import_body_images --limit 100   # first 100 unique images only

Options:
    --source-base   Base URL to fetch images from
                    (default: https://www.fpsu.org.ua)
    --workers       Number of parallel download threads (default 4)
    --limit         Max unique images to process (0 = all)
    --timeout       HTTP request timeout in seconds (default 15)
    --folder        Cloudinary folder for uploaded images (default: fpsu/body)
    --dry-run       Print image list without downloading or uploading.
"""
from __future__ import annotations

import re
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import Any

import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.news.models import Article
from apps.pages.models import StaticPage

_SRC_RE = re.compile(r'(src|href)="(https?://www\.fpsu\.org\.ua/images/[^"]+)"', re.IGNORECASE)
_FPSU_BASE = "https://www.fpsu.org.ua"


def _collect_image_urls(bodies: list[str]) -> set[str]:
    """Return the set of unique fpsu.org.ua image URLs found in all body strings."""
    urls: set[str] = set()
    for body in bodies:
        for m in _SRC_RE.finditer(body):
            urls.add(m.group(2))
    return urls


def _cloudinary_public_id(url: str, folder: str) -> str:
    """Derive a stable Cloudinary public_id from the image URL path."""
    path = url.replace(_FPSU_BASE + "/images/", "").lstrip("/")
    # Strip extension — Cloudinary manages format itself
    public_id = Path(path).with_suffix("").as_posix()
    return f"{folder}/{public_id}"


def _download_and_upload(
    url: str,
    folder: str,
    timeout: int,
) -> tuple[str, str | None]:
    """
    Download image from `url` and upload to Cloudinary.
    Returns (original_url, cloudinary_url_or_None).
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError) as exc:
        return url, None

    public_id = _cloudinary_public_id(url, folder)
    try:
        result = cloudinary.uploader.upload(
            BytesIO(data),
            public_id=public_id,
            overwrite=False,
            resource_type="image",
        )
        return url, result.get("secure_url") or result.get("url")
    except Exception:
        return url, None


class Command(BaseCommand):
    help = "Download inline images from body HTML and upload to Cloudinary"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--source-base", default=_FPSU_BASE,
            help="Base URL images are fetched from",
        )
        parser.add_argument("--workers", type=int, default=4)
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--timeout", type=int, default=15)
        parser.add_argument("--folder", default="fpsu/body")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        folder: str = options["folder"]
        workers: int = options["workers"]
        limit: int = options["limit"]
        timeout: int = options["timeout"]
        dry_run: bool = options["dry_run"]

        # ── Collect all bodies ────────────────────────────────────────────────
        self.stdout.write("Collecting bodies from Article and StaticPage …")
        article_bodies = list(
            Article.objects.exclude(body="").values_list("id", "body")
        )
        page_bodies = list(
            StaticPage.objects.exclude(body="").values_list("id", "body")
        )
        all_bodies = [b for _, b in article_bodies] + [b for _, b in page_bodies]
        self.stdout.write(
            f"  {len(article_bodies)} articles + {len(page_bodies)} pages = "
            f"{len(all_bodies)} total bodies."
        )

        # ── Find unique image URLs ────────────────────────────────────────────
        image_urls = _collect_image_urls(all_bodies)
        self.stdout.write(f"  {len(image_urls)} unique fpsu.org.ua image URLs found.")

        if limit:
            image_urls = set(list(image_urls)[:limit])
            self.stdout.write(f"  Limited to {len(image_urls)} images (--limit).")

        if not image_urls:
            self.stdout.write("Nothing to do.")
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — sample URLs:"))
            for url in list(image_urls)[:20]:
                self.stdout.write(f"  {url}")
            return

        # ── Download + upload ─────────────────────────────────────────────────
        self.stdout.write(
            f"Downloading & uploading {len(image_urls)} images "
            f"({workers} workers, timeout={timeout}s) …"
        )
        url_map: dict[str, str] = {}  # original → cloudinary URL
        failed: list[str] = []
        done = 0

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_download_and_upload, url, folder, timeout): url
                for url in image_urls
            }
            for future in as_completed(futures):
                original, cdn_url = future.result()
                done += 1
                if cdn_url:
                    url_map[original] = cdn_url
                else:
                    failed.append(original)
                if done % 100 == 0:
                    self.stdout.write(
                        f"  {done}/{len(image_urls)} done, "
                        f"{len(url_map)} ok, {len(failed)} failed …"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Uploaded {len(url_map)} images. {len(failed)} failed."
            )
        )
        if failed:
            self.stdout.write(self.style.WARNING("Failed URLs (first 20):"))
            for u in failed[:20]:
                self.stdout.write(f"  {u}")

        if not url_map:
            self.stdout.write("No images uploaded — bodies not updated.")
            return

        # ── Rewrite bodies ────────────────────────────────────────────────────
        def _replace(html: str) -> str:
            def _sub(m: re.Match) -> str:
                cdn = url_map.get(m.group(2))
                if cdn:
                    return f'{m.group(1)}="{cdn}"'
                return m.group(0)
            return _SRC_RE.sub(_sub, html)

        self.stdout.write("Rewriting Article.body …")
        arts_updated = 0
        arts_to_save: list[Article] = []
        for art_id, body in article_bodies:
            new_body = _replace(body)
            if new_body != body:
                arts_to_save.append(Article(id=art_id, body=new_body))

        if arts_to_save:
            with transaction.atomic():
                Article.objects.bulk_update(arts_to_save, ["body"], batch_size=500)
            arts_updated = len(arts_to_save)
        self.stdout.write(f"  {arts_updated} articles updated.")

        self.stdout.write("Rewriting StaticPage.body …")
        pages_updated = 0
        pages_to_save: list[StaticPage] = []
        for page_id, body in page_bodies:
            new_body = _replace(body)
            if new_body != body:
                pages_to_save.append(StaticPage(id=page_id, body=new_body))

        if pages_to_save:
            with transaction.atomic():
                StaticPage.objects.bulk_update(pages_to_save, ["body"], batch_size=200)
            pages_updated = len(pages_to_save)
        self.stdout.write(f"  {pages_updated} pages updated.")

        self.stdout.write(self.style.SUCCESS("Done."))
