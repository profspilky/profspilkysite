"""
Management command: seed body content for the main navigation section pages.

These pages are Joomla category index pages — they aggregate sub-sections
rather than linking to a single article, so import_bodies leaves them empty.
This command populates them with a description + sub-section link list.

For activity direction pages (/napryamki-diyalnosti/*), the body also includes
a direct link to the corresponding news category, since those pages in Joomla
showed a live news list, not static content.

Idempotent: uses update_or_create keyed on url_path.

Usage:
    python manage.py seed_section_pages
    python manage.py seed_section_pages --dry-run
"""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.pages.models import StaticPage

# Each entry: url_path → (title, description, children, news_category_path)
# news_category_path: if set, a "Переглянути всі новини" link is added
_SECTIONS: list[dict] = [
    # ── Про ФПУ ──────────────────────────────────────────────────────────────
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
        "news_category_path": None,
    },
    {
        "url_path": "/pro-fpu/kerivnitstvo-fpu",
        "title": "Керівництво ФПУ",
        "description": (
            "Федерацію профспілок України очолює обраний з'їздом Голова ФПУ. "
            "Керівництво здійснює загальне управління діяльністю Федерації, "
            "представляє її інтереси у відносинах з органами державної влади, "
            "роботодавцями та міжнародними організаціями."
        ),
        "children": [
            ("Виборні органи ФПУ",  "/pro-fpu/viborchi-organi-fpu"),
            ("Президія ФПУ",        "/pro-fpu/prezidiya"),
            ("Комісії ФПУ",         "/pro-fpu/komissii-fpu"),
        ],
        "news_category_path": None,
    },
    {
        "url_path": "/pro-fpu/chlenski-organizatsiji",
        "title": "Членські організації ФПУ",
        "description": (
            "До складу Федерації профспілок України входять всеукраїнські галузеві профспілки "
            "та територіальні об'єднання організацій профспілок. Вони об'єднують мільйони "
            "членів у всіх регіонах та галузях економіки України."
        ),
        "children": [
            ("Всеукраїнські галузеві профспілки",                "/pro-fpu/chlenski-organizatsiji"),
            ("Територіальні об'єднання організацій профспілок",  "/pro-fpu/chlenski-organizatsiji"),
        ],
        "news_category_path": "nasha-borotba/novini-chlenskikh-organizatsij",
    },
    {
        "url_path": "/pro-fpu/komissii-fpu",
        "title": "Комісії ФПУ",
        "description": (
            "Постійні комісії ФПУ є дорадчими органами Ради та Президії Федерації. "
            "Вони здійснюють підготовку і попередній розгляд питань, що стосуються "
            "основних напрямів діяльності профспілок."
        ),
        "children": [
            ("Виборні органи ФПУ",  "/pro-fpu/viborchi-organi-fpu"),
            ("Президія ФПУ",        "/pro-fpu/prezidiya"),
        ],
        "news_category_path": None,
    },
    {
        "url_path": "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok",
        "title": "Законодавче регулювання діяльності профспілок",
        "description": (
            "Діяльність профспілок в Україні регулюється Конституцією України, "
            "Законом України «Про професійні спілки, їх права та гарантії діяльності», "
            "Кодексом законів про працю та іншими нормативно-правовими актами."
        ),
        "children": [
            ("Документи ФПУ",                 "/dokumenti-fpu"),
            ("Статут ФПУ",                    "/dokumenti-fpu/statut-fpu"),
            ("Постанови Ради ФПУ",            "/dokumenti-fpu/postanovi-radi-fpu"),
            ("Постанови Президії ФПУ",        "/dokumenti-fpu/postanovi-prezidiji-fpu"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist",
    },

    # ── Напрями діяльності — головна ─────────────────────────────────────────
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
        "news_category_path": None,
    },

    # ── Напрями діяльності — під-сторінки ────────────────────────────────────
    {
        "url_path": "/napryamki-diyalnosti/pravovij-zakhist",
        "title": "Правовий захист",
        "description": (
            "ФПУ здійснює системну правозахисну роботу: веде переговори з роботодавцями "
            "та органами влади, надає безоплатні юридичні консультації членам профспілок, "
            "представляє їхні інтереси у судах та перед державними органами. "
            "Правовий захист — ключовий напрям діяльності профспілкового руху."
        ),
        "children": [
            ("Напрями діяльності",         "/napryamki-diyalnosti"),
            ("Документи ФПУ",              "/dokumenti-fpu"),
            ("Постанови Ради ФПУ",         "/dokumenti-fpu/postanovi-radi-fpu"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist",
    },
    {
        "url_path": "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya",
        "title": "Охорона праці і здоров'я",
        "description": (
            "Профспілки забезпечують дотримання вимог законодавства про охорону праці, "
            "здійснюють громадський контроль за умовами праці та безпекою на виробництві. "
            "ФПУ бере активну участь у розробці нормативних актів у сфері охорони праці, "
            "взаємодіє з Державною службою з питань праці та роботодавцями."
        ),
        "children": [
            ("Напрями діяльності",  "/napryamki-diyalnosti"),
            ("Правовий захист",     "/napryamki-diyalnosti/pravovij-zakhist"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/okhorona-pratsi-i-zdorov-ya",
    },
    {
        "url_path": "/napryamki-diyalnosti/sotsialnij-zakhist",
        "title": "Соціальний захист",
        "description": (
            "ФПУ відстоює гідний рівень заробітної плати, пенсій та соціальних виплат. "
            "Профспілки беруть участь у тристоронніх переговорах у рамках Національної "
            "тристоронньої соціально-економічної ради, домагаються підвищення мінімальної "
            "заробітної плати та індексації доходів відповідно до зростання цін."
        ),
        "children": [
            ("Напрями діяльності",                                        "/napryamki-diyalnosti"),
            ("Соціальний діалог",                                          "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"),
            ("Соціальне страхування і пенсійне забезпечення",             "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/sotsialnij-zakhist",
    },
    {
        "url_path": "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya",
        "title": "Виробнича політика та ціноутворення",
        "description": (
            "Профспілки беруть участь у формуванні державної промислової та цінової політики. "
            "ФПУ відстоює інтереси працівників у питаннях тарифного регулювання, "
            "збереження виробничого потенціалу країни та забезпечення зайнятості населення."
        ),
        "children": [
            ("Напрями діяльності",    "/napryamki-diyalnosti"),
            ("Соціальний захист",     "/napryamki-diyalnosti/sotsialnij-zakhist"),
            ("Соціальний діалог",     "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/vyrobnycha-polityka-ta-tsinoutvorennia",
    },
    {
        "url_path": "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya",
        "title": "Соціальне страхування і пенсійне забезпечення",
        "description": (
            "ФПУ представляє інтереси застрахованих осіб у фондах соціального страхування "
            "та Пенсійному фонді України. Профспілки беруть участь в управлінні системою "
            "соціального захисту, добиваються підвищення пенсій та страхових виплат, "
            "захисту прав працівників на гідне пенсійне забезпечення."
        ),
        "children": [
            ("Напрями діяльності",    "/napryamki-diyalnosti"),
            ("Соціальний захист",     "/napryamki-diyalnosti/sotsialnij-zakhist"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya",
    },
    {
        "url_path": "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya",
        "title": "Соціальний діалог та колективно-договірне регулювання",
        "description": (
            "Соціальний діалог — ключовий інструмент взаємодії профспілок, роботодавців "
            "і держави. ФПУ бере участь у переговорах на всіх рівнях: від підприємства "
            "до національного. Колективні договори та угоди забезпечують гарантії "
            "трудових прав мільйонів найманих працівників."
        ),
        "children": [
            ("Напрями діяльності",    "/napryamki-diyalnosti"),
            ("Соціальний захист",     "/napryamki-diyalnosti/sotsialnij-zakhist"),
            ("Постанови Ради ФПУ",   "/dokumenti-fpu/postanovi-radi-fpu"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/sotsialnij-dialog",
    },
    {
        "url_path": "/napryamki-diyalnosti/organizatsijna-robota",
        "title": "Організаційна робота",
        "description": (
            "Організаційна робота спрямована на зміцнення профспілкових лав, "
            "підвищення ефективності діяльності первинних організацій та забезпечення "
            "представництва інтересів членів профспілок на всіх рівнях. "
            "ФПУ підтримує навчання профспілкових кадрів і активістів."
        ),
        "children": [
            ("Напрями діяльності",         "/napryamki-diyalnosti"),
            ("Членські організації",       "/pro-fpu/chlenski-organizatsiji"),
            ("Молодіжна політика",         "/napryamki-diyalnosti/molodizhna-politika"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/organizatsionnaya-rabota",
    },
    {
        "url_path": "/napryamki-diyalnosti/molodizhna-politika",
        "title": "Молодіжна політика",
        "description": (
            "ФПУ приділяє особливу увагу роботі з молоддю. Молодіжні комісії та ради "
            "діють у складі профспілкових організацій усіх рівнів. Профспілки сприяють "
            "працевлаштуванню молоді, захищають її трудові права та інтереси, "
            "підтримують розвиток молодіжного активу."
        ),
        "children": [
            ("Напрями діяльності",         "/napryamki-diyalnosti"),
            ("Організаційна робота",       "/napryamki-diyalnosti/organizatsijna-robota"),
            ("Членські організації",       "/pro-fpu/chlenski-organizatsiji"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/molodizhna-politika",
    },
    {
        "url_path": "/napryamki-diyalnosti/informatsijna-robota",
        "title": "Інформаційна робота",
        "description": (
            "Інформаційна діяльність ФПУ спрямована на висвітлення роботи профспілок, "
            "формування позитивного іміджу профспілкового руху та інформування суспільства "
            "про захист трудових прав. ФПУ підтримує власні медіа та активно присутня "
            "у соціальних мережах."
        ),
        "children": [
            ("Напрями діяльності",   "/napryamki-diyalnosti"),
            ("Фотогалерея",          "/gallery/"),
            ("Новини ФПУ",           "/materiali/"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/informatsijna-robota",
    },
    {
        "url_path": "/napryamki-diyalnosti/mizhnarodna-robota",
        "title": "Міжнародна робота",
        "description": (
            "ФПУ є членом Міжнародної організації праці (МОП), Міжнародної конфедерації "
            "профспілок (МКП), Панєвропейської регіональної ради МКП та Загальноєвропейської "
            "ради профспілок (ЄКП). Міжнародна діяльність спрямована на захист прав "
            "трудових мігрантів та інтеграцію до European Trade Union Confederation."
        ),
        "children": [
            ("Напрями діяльності",   "/napryamki-diyalnosti"),
            ("Новини ФПУ",           "/materiali/"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/mizhnarodna-robota",
    },

    # ── Документи ────────────────────────────────────────────────────────────
    {
        "url_path": "/dokumenti-fpu",
        "title": "Документи ФПУ",
        "description": (
            "Офіційні документи Федерації профспілок України: постанови, статут, стратегія "
            "розвитку, матеріали з'їздів та інші нормативні акти, що регулюють діяльність "
            "профспілкового руху."
        ),
        "children": [
            ("Матеріали VII З'їзду ФПУ",           "/dokumenti-fpu/materiali-vii-z-jizdu-federatsiji-profspilok-ukrajini"),
            ("Матеріали VIII З'їзду ФПУ",          "/dokumenti-fpu/materiali-viii-z-jizdu-federatsiji-profspilok-ukrajini"),
            ("Постанови Ради ФПУ",                 "/dokumenti-fpu/postanovi-radi-fpu"),
            ("Постанови Президії ФПУ",             "/dokumenti-fpu/postanovi-prezidiji-fpu"),
            ("Статут ФПУ",                         "/dokumenti-fpu/statut-fpu"),
            ("Стратегія діяльності ФПУ 2021–2026", "/dokumenti-fpu/stratehiia-diialnosti-fpu-na-2021-2026-roky"),
            ("Репрезентативність",                  "/dokumenti-fpu/reprezentatyvnist"),
        ],
        "news_category_path": None,
    },
]


def _build_body(description: str, children: list[tuple[str, str]], news_cat_path: str | None) -> str:
    """
    Будує HTML-тіло для сторінки:
    - intro paragraph з описом
    - список посилань на підрозділи
    - якщо є news_cat_path — блок з посиланням на стрічку новин цього напряму
    """
    links = "\n".join(
        f'    <li><a href="{href}">{label}</a></li>'
        for label, href in children
    )
    body = (
        f'<p class="section-intro">{description}</p>\n'
        f'<ul class="section-nav">\n{links}\n</ul>'
    )
    if news_cat_path:
        body += (
            f'\n\n<div class="section-news-link">'
            f'<a href="/{news_cat_path}/" class="btn btn--primary">'
            f'Переглянути всі новини за цим напрямом →</a></div>'
        )
    return body


class Command(BaseCommand):
    help = "Seed body content for main navigation section pages (idempotent)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        created_count = updated_count = 0

        for section in _SECTIONS:
            url_path = section["url_path"]
            news_cat = section.get("news_category_path")
            body = _build_body(section["description"], section["children"], news_cat)
            defaults = {
                "title": section["title"],
                "body": body,
                "is_published": True,
                "joomla_type": "menu",
            }

            # Both /path and /path.html variants exist (import_pages creates both).
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
