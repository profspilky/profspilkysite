"""
Management command: seed the Priority model with the 4 core ФПУ priorities.

Idempotent — uses update_or_create keyed on icon_key, so re-running is safe.

Usage:
    python manage.py seed_priorities
    python manage.py seed_priorities --dry-run
"""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.models import Priority, PriorityIcon

_PRIORITIES: list[dict] = [
    {
        "icon_key": PriorityIcon.SHIELD,
        "title": "Правовий Захист",
        "description": (
            "Забезпечуємо дотримання трудових прав та представляємо "
            "інтереси працівників у судах, переговорах і законодавчих органах."
        ),
        "order": 1,
    },
    {
        "icon_key": PriorityIcon.HARD_HAT,
        "title": "Безпека Праці",
        "description": (
            "Контролюємо умови роботи, запобігаємо виробничим травмам "
            "і нещасним випадкам, впроваджуємо стандарти охорони праці."
        ),
        "order": 2,
    },
    {
        "icon_key": PriorityIcon.DIALOG,
        "title": "Соціальний Діалог",
        "description": (
            "Ведемо переговори з роботодавцями та урядом, укладаємо "
            "колективні договори на захист інтересів кожного члена профспілки."
        ),
        "order": 3,
    },
    {
        "icon_key": PriorityIcon.HEART,
        "title": "Як Ми Допомагаємо",
        "description": (
            "Надаємо юридичну, матеріальну та психологічну підтримку членам "
            "профспілки у складних життєвих і виробничих ситуаціях."
        ),
        "order": 4,
    },
]


class Command(BaseCommand):
    help = "Seed the Priority model with 4 core ФПУ priorities (idempotent)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        created_count = updated_count = 0

        for data in _PRIORITIES:
            icon_key = data["icon_key"]
            defaults = {k: v for k, v in data.items() if k != "icon_key"}

            if dry_run:
                exists = Priority.objects.filter(icon_key=icon_key).exists()
                self.stdout.write(
                    f"  {'UPDATE' if exists else 'CREATE'} [{icon_key}] {data['title']}"
                )
                if exists:
                    updated_count += 1
                else:
                    created_count += 1
                continue

            _, was_created = Priority.objects.update_or_create(
                icon_key=icon_key,
                defaults=defaults,
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Priorities: {created_count} created, {updated_count} updated."
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
