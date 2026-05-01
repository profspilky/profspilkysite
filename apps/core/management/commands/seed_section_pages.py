"""
Management command: seed body content for the main navigation section pages.

These pages are Joomla category index pages — they aggregate sub-sections
rather than linking to a single article, so import_bodies leaves them empty.
This command populates them with a description + sub-section link list.

Idempotent: uses update_or_create keyed on url_path.

Usage:
    python manage.py seed_section_pages
    python manage.py seed_section_pages --dry-run
"""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.pages.models import StaticPage

# Each entry: url_path → (title, description, list of (label, href))
_SECTIONS: list[dict] = [
    {
        "url_path": "/pro-fpu",
        "title": "Про ФПУ",
        "description": (
            "Федерація профспілок України — найбільше об'єднання профспілок країни, "
            "що об'єднує мільйони працівників різних галузей. Ми захищаємо трудові права, "
            "забезпечуємо гідні умови праці та відстоюємо соціальну справедливість."
        ),
        "children": [
            ("Історія ФПУ",                          "/pro-fpu/istoriya-fpu"),
            ("Виборні органи ФПУ",                   "/pro-fpu/viborchi-organi-fpu"),
            ("Керівництво ФПУ",                      "/pro-fpu/kerivnitstvo-fpu"),
            ("Президія",                             "/pro-fpu/prezidiya"),
            ("Членські організації",                 "/pro-fpu/chlenski-organizatsiji"),
            ("Комісії ФПУ",                          "/pro-fpu/komissii-fpu"),
            ("Законодавче регулювання діяльності",   "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok"),
            ("Символіка ФПУ",                        "/pro-fpu/simvolika-fpu"),
        ],
    },
    {
        "url_path": "/napryamki-diyalnosti",
        "title": "Напрями діяльності",
        "description": (
            "ФПУ веде системну роботу за всіма ключовими напрямами захисту прав працівників: "
            "від правового супроводу до охорони праці, від соціального страхування до молодіжної "
            "і міжнародної діяльності."
        ),
        "children": [
            ("Правовий захист",                                      "/napryamki-diyalnosti/pravovij-zakhist"),
            ("Охорона праці і здоров'я",                             "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya"),
            ("Соціальний захист",                                    "/napryamki-diyalnosti/sotsialnij-zakhist"),
            ("Виробнича політика та ціноутворення",                  "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya"),
            ("Соціальне страхування і пенсійне забезпечення",        "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya"),
            ("Соціальний діалог та колективно-договірне регулювання", "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"),
            ("Організаційна робота",                                  "/napryamki-diyalnosti/organizatsijna-robota"),
            ("Молодіжна політика",                                    "/napryamki-diyalnosti/molodizhna-politika"),
            ("Інформаційна робота",                                   "/napryamki-diyalnosti/informatsijna-robota"),
            ("Міжнародна робота",                                     "/napryamki-diyalnosti/mizhnarodna-robota"),
        ],
    },
    {
        "url_path": "/dokumenti-fpu",
        "title": "Документи ФПУ",
        "description": (
            "Офіційні документи Федерації профспілок України: постанови, статут, стратегія "
            "розвитку, матеріали з'їздів та інші нормативні акти, що регулюють діяльність "
            "профспілкового руху."
        ),
        "children": [
            ("Матеріали VII З'їзду ФПУ",           "/dokumenti-fpu/materiali-vii-z-jizdu-federatsiji-profspilok-ukraini"),
            ("Матеріали VIII З'їзду ФПУ",          "/dokumenti-fpu/materiali-viii-z-jizdu-fpu"),
            ("Постанови Ради ФПУ",                 "/dokumenti-fpu/postanovi-radi-fpu"),
            ("Постанови Президії ФПУ",             "/dokumenti-fpu/postanovi-prezidiji-fpu"),
            ("Статут ФПУ",                         "/dokumenti-fpu/statut-fpu"),
            ("Стратегія діяльності ФПУ 2021–2026", "/dokumenti-fpu/stratehiia-diialnosti-fpu-na-2021-2026-roky"),
            ("Репрезентативність",                  "/dokumenti-fpu/reprezentatyvnist"),
        ],
    },
]


def _build_body(description: str, children: list[tuple[str, str]]) -> str:
    links = "\n".join(
        f'    <li><a href="{href}">{label}</a></li>'
        for label, href in children
    )
    return (
        f'<p class="section-intro">{description}</p>\n'
        f'<ul class="section-nav">\n{links}\n</ul>'
    )


class Command(BaseCommand):
    help = "Seed body content for main navigation section pages (idempotent)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        created_count = updated_count = 0

        for section in _SECTIONS:
            url_path = section["url_path"]
            body = _build_body(section["description"], section["children"])
            defaults = {
                "title": section["title"],
                "body": body,
                "is_published": True,
                "joomla_type": "menu",
            }

            # Both /path and /path.html variants exist (import_pages creates both).
            # The view looks for the .html variant first, so both must have body.
            for variant in (url_path, url_path + ".html"):
                if dry_run:
                    exists = StaticPage.objects.filter(url_path=variant).exists()
                    action = "UPDATE" if exists else "CREATE"
                    self.stdout.write(f"  {action} {variant} — {section['title']}")
                    if exists:
                        updated_count += 1
                    else:
                        created_count += 1
                    continue

                _, was_created = StaticPage.objects.update_or_create(
                    url_path=variant,
                    defaults=defaults,
                )
                if was_created:
                    created_count += 1
                    self.stdout.write(f"  CREATED  {variant}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  UPDATED  {variant}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Section pages: {created_count} created, {updated_count} updated."
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
