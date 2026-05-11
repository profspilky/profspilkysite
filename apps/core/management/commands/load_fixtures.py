"""
Management command: load_fixtures

True streaming replacement for Django's `loaddata`.

Why the naive approach OOM-crashes on Render Starter (512 MB):
  json.loads(251 MB string) → ~500 MB in memory
  + 30 K Django objects     → ~150 MB
  Total ≈ 1 GB → OOM-kill

This command uses ijson to parse the JSON array one element at a time.
At any moment only `batch_size` raw dicts are in memory (~2–4 MB).

Requirements:
  pip install ijson  (already in requirements.txt)

The fixture MUST be exported in FK-dependency order, e.g.:
  python manage.py dumpdata \\
      news.category news.article \\
      pages.staticpage \\
      gallery.galleryalbum gallery.galleryphoto \\
      documents.documentcategory documents.document \\
      --natural-foreign --output tools/data/fixtures.json.gz

Usage:
    python manage.py load_fixtures tools/data/fixtures.json.gz
    python manage.py load_fixtures tools/data/fixtures.json.gz --batch-size 100
"""
from __future__ import annotations

import gzip
import json
import time
from typing import Any

import ijson

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Stream-load a gzipped JSON fixture (low memory, batched transactions)"

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

        self.stdout.write(f"  Fixture: {fixture_path}")
        self.stdout.write(f"  Batch size: {batch_size}")

        t0 = time.monotonic()
        loaded = 0
        batch: list[dict] = []
        current_model: str | None = None

        def flush(model_label: str, items: list[dict]) -> int:
            """Deserialize and save one batch. Returns number of saved objects."""
            if not items:
                return 0
            batch_json = json.dumps(items)
            # Ensure connection is alive before each batch (Render Free Postgres
            # drops idle SSL connections; close() triggers a fresh reconnect).
            connection.ensure_connection()
            with transaction.atomic():
                for obj in serializers.deserialize("json", batch_json):
                    obj.save()
            return len(items)

        try:
            with gzip.open(fixture_path, "rb") as fh:
                for item in ijson.items(fh, "item"):
                    model_label: str = item["model"]

                    # When model changes → flush accumulated batch first
                    if model_label != current_model:
                        if batch and current_model:
                            n = flush(current_model, batch)
                            loaded += n
                            elapsed = time.monotonic() - t0
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✓ {current_model}: {n}  (total {loaded}, {elapsed:.0f}s)"
                                )
                            )
                        batch = []
                        current_model = model_label
                        self.stdout.write(f"  → {model_label} …")

                    batch.append(item)

                    if len(batch) >= batch_size:
                        n = flush(current_model, batch)  # type: ignore[arg-type]
                        loaded += n
                        batch = []
                        elapsed = time.monotonic() - t0
                        self.stdout.write(
                            f"    {loaded} об'єктів ({elapsed:.0f}s)", ending="\r"
                        )
                        self.stdout.flush()

        except (OSError, EOFError) as exc:
            raise CommandError(f"Помилка читання {fixture_path}: {exc}") from exc

        # Flush last model's remaining items
        if batch and current_model:
            n = flush(current_model, batch)
            loaded += n
            elapsed = time.monotonic() - t0
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ {current_model}: {n}  (total {loaded}, {elapsed:.0f}s)"
                )
            )

        elapsed_total = time.monotonic() - t0
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ load_fixtures завершено: {loaded} об'єктів за {elapsed_total:.1f}s"
            )
        )
