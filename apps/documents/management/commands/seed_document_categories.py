"""Seed default document categories from the original FPU website menu."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.documents.models import DocumentCategory

CATEGORIES = [
    {"title": "Матеріали VII З'їзду Федерації профспілок України", "slug": "materialy-vii-zyizdu-fpu", "order": 1},
    {"title": "Матеріали VIII З'їзду Федерації профспілок України", "slug": "materialy-viii-zyizdu-fpu", "order": 2},
    {"title": "Постанови Ради ФПУ", "slug": "postanovi-radi-fpu", "order": 3},
    {"title": "Постанови Президії ФПУ", "slug": "postanovi-prezidiji-fpu", "order": 4},
    {"title": "Статут ФПУ", "slug": "statut-fpu", "order": 5},
    {"title": "Стратегія діяльності ФПУ на 2021–2026 роки", "slug": "strategiya-diyalnosti-fpu-2021-2026", "order": 6},
    {"title": "Репрезентативність", "slug": "reprezentativnist", "order": 7},
    {"title": "Галузеві угоди", "slug": "galuzevi-ugodi", "order": 8},
    {"title": "Генеральна угода", "slug": "generalna-ugoda", "order": 9},
    {"title": "Законодавство про профспілки", "slug": "zakonodavstvo-pro-profspilky", "order": 10},
]


class Command(BaseCommand):
    help = "Seed default document categories."

    def handle(self, *args, **options) -> None:
        created = 0
        for data in CATEGORIES:
            _, was_created = DocumentCategory.objects.get_or_create(
                slug=data["slug"],
                defaults={"title": data["title"], "order": data["order"]},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Done: {created} categories created."))
