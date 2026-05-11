"""
Management command: load_fixtures

Replaces Django's built-in `loaddata` for large gzipped JSON fixtures.
Splits loading into batches so each transaction stays small → no SSL
connection timeout on Render / Heroku / other hosted PostgreSQL.

Usage:
    python manage.py load_fixtures tools/data/fixtures.json.gz
    python manage.py load_fixtures tools/data/fixtures.json.gz --batch-size 100
"""
from __future__ import annotations

import gzip
import time
from typing import Any

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Load gzipped JSON fixture in small batches (avoids PostgreSQL SSL timeout)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("fixture", help="Path to .json.gz fixture file")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Objects per transaction (default: 200)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        fixture_path: str = options["fixture"]
        batch_size: int = options["batch_size"]

        # ── Read ──────────────────────────────────────────────────────────────
        self.stdout.write(f"  Читання {fixture_path} …")
        try:
            with gzip.open(fixture_path, "rb") as fh:
                raw = fh.read()
        except (OSError, EOFError) as exc:
            raise CommandError(f"Не вдалося відкрити {fixture_path}: {exc}") from exc

        file_mb = len(raw) / 1_048_576
        self.stdout.write(f"  Розмір: {file_mb:.1f} MB")

        # ── Deserialize ───────────────────────────────────────────────────────
        self.stdout.write("  Десеріалізація …")
        t0 = time.monotonic()
        try:
            objects = list(serializers.deserialize("json", raw))
        except Exception as exc:
            raise CommandError(f"Помилка десеріалізації: {exc}") from exc

        total = len(objects)
        self.stdout.write(f"  Об'єктів: {total}  ({time.monotonic() - t0:.1f}s)")

        # ── Batch load ────────────────────────────────────────────────────────
        self.stdout.write(f"  Завантаження батчами по {batch_size} …")
        t1 = time.monotonic()
        loaded = 0

        for start in range(0, total, batch_size):
            batch = objects[start : start + batch_size]
            with transaction.atomic():
                for obj in batch:
                    obj.save()
                loaded += len(batch)

            pct = loaded * 100 // total
            elapsed = time.monotonic() - t1
            self.stdout.write(
                f"  {loaded}/{total}  {pct}%  ({elapsed:.0f}s)",
                ending="\r",
            )
            self.stdout.flush()

        self.stdout.write("")
        elapsed_total = time.monotonic() - t0
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ load_fixtures: {loaded} об'єктів за {elapsed_total:.1f}s"
            )
        )
