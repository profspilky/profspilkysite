"""Seed FPU leadership team members from public information."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.models import TeamMember

TEAM = [
    {
        "full_name": "Сергій Бизов",
        "role": "Голова Федерації профспілок України",
        "bio": "Очолює Федерацію профспілок України. Займається захистом трудових прав, "
               "соціальним діалогом та міжнародним співробітництвом.",
        "order": 1,
    },
    {
        "full_name": "Олег Осіпенко",
        "role": "Перший заступник Голови ФПУ",
        "bio": "Координує роботу з правового захисту та колективно-договірного регулювання.",
        "order": 2,
    },
    {
        "full_name": "Валентина Жайворон",
        "role": "Заступник Голови ФПУ",
        "bio": "Відповідає за організаційну роботу та взаємодію з членськими організаціями.",
        "order": 3,
    },
    {
        "full_name": "Сергій Українець",
        "role": "Заступник Голови ФПУ",
        "bio": "Координує питання охорони праці, безпеки виробництва та соціального страхування.",
        "order": 4,
    },
]


class Command(BaseCommand):
    help = "Seed FPU team members."

    def handle(self, *args, **options) -> None:
        created = 0
        for data in TEAM:
            _, was_created = TeamMember.objects.get_or_create(
                full_name=data["full_name"],
                defaults={
                    "role": data["role"],
                    "bio": data["bio"],
                    "order": data["order"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Done: {created} team members created."))
