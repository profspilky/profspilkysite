"""
Management command: seed Document records from StaticPage bodies and hardcoded data.

Sources per category:
  postanovi-radi-fpu          – parses /dokumenti-fpu/postanovi-radi-fpu StaticPage body
  postanovi-prezidiji-fpu     – parses /dokumenti-fpu/postanovi-prezidiji-fpu StaticPage body
  materialy-vii-zyizdu-fpu    – hardcoded list
  materialy-viii-zyizdu-fpu   – hardcoded list
  statut-fpu                  – hardcoded
  strategiya-diyalnosti-*     – hardcoded
  reprezentativnist           – hardcoded
  galuzevi-ugodi              – hardcoded (реєстр угод)
  generalna-ugoda             – hardcoded list of Генеральні угоди
  zakonodavstvo-pro-profspilky – hardcoded external links

Usage:
    python manage.py seed_documents
    python manage.py seed_documents --dry-run
    python manage.py seed_documents --clear
"""
from __future__ import annotations

import datetime
import re
from typing import Any

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.documents.models import Document, DocumentCategory, FileType
from apps.pages.models import StaticPage

_DATE_RE = re.compile(r"від\s+(\d{2})\.(\d{2})\.(\d{4})", re.IGNORECASE)


def _file_type(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".pdf"):
        return FileType.PDF
    if lower.endswith((".doc", ".docx")):
        return FileType.DOC
    if lower.endswith((".xls", ".xlsx")):
        return FileType.XLS
    return FileType.OTHER


def _parse_date(text: str) -> datetime.date | None:
    m = _DATE_RE.search(text)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _parse_postanovy(html: str) -> list[dict]:
    """
    Parse Постанови HTML body.

    Pattern:
      <p>...<strong>ЗАСІДАННЯ ... від DD.MM.YYYY</strong>...</p>  ← date heading
      <p>...<a href="URL">Resolution number</a> «Title»...</p>    ← document
    """
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    current_date: datetime.date | None = None

    for tag in soup.find_all("p"):
        text = tag.get_text(separator=" ", strip=True)
        strong = tag.find("strong")
        if strong:
            d = _parse_date(text)
            if d:
                current_date = d
                continue

        a_tag = tag.find("a", href=True)
        if not a_tag:
            continue
        href = a_tag["href"].strip()
        if not href.startswith("http"):
            continue
        full_title = text.strip()
        if not full_title:
            full_title = a_tag.get_text(strip=True)
        if not full_title:
            continue
        items.append({
            "title": full_title[:500],
            "file_url": href,
            "file_type": _file_type(href),
            "published_at": current_date,
        })

    return items


# ── Hardcoded data ────────────────────────────────────────────────────────────

_STATUT = [
    {
        "title": "Статут Федерації профспілок України (редакція 2021, з печатками)",
        "file_url": "https://www.fpsu.org.ua/images/images/2023/June/260623/"
                    "Статут_ФПУ_2021_в_кольорі_з_печатками.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
]

_STRATEGY = [
    {
        "title": 'Стратегія діяльності ФПУ на 2021–2026 роки «Час дій та якісних змін»',
        "file_url": "https://www.fpsu.org.ua/images/documents/СТРАТЕГІЯ_web.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
]

_REPREZENT = [
    {
        "title": "Репрезентативність Федерації профспілок України",
        "file_url": "https://www.fpsu.org.ua/images/репрезентативність.doc",
        "file_type": FileType.DOC,
        "published_at": None,
    },
]

_VII_ZJIZD = [
    {
        "title": "Постанова №7з-1 — Про підтвердження повноважень делегатів VII З'їзду ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/7з-1_Делегати.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-2 — Про Регламент VII З'їзду ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-2_%D0%9F%D1%80%D0%BE_%D0%A0%D0%B5%D0%B3%D0%BB%D0%B0%D0%BC%D0%B5%D0%BD%D1%82_%D0%97%D1%97%D0%B7%D0%B4%D1%83.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-3 — Про Звіт Ради ФПУ та Стратегію 2016–2021 «Європейський вибір»",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-3__%D0%9F%D1%80%D0%BE_%D0%97%D0%B2%D1%96%D1%82_%D1%96_%D0%A1%D1%82%D0%B0%D1%80%D1%82%D0%B5%D0%B3%D1%96%D1%8E.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-4 — Про Звіт Контрольно-ревізійної комісії ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-4__%D0%B7%D0%B2%D1%96%D1%82_%D0%9A%D0%A0%D0%9A.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-5 — Про Звіт Статутної комісії ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-5_%D0%B7%D0%B2%D1%96%D1%82_%D0%A1%D1%82%D0%B0%D1%82%D1%83%D1%82%D0%BD%D0%BE%D1%97_%D0%BA%D0%BE%D0%BC%D1%96%D1%81%D1%96%D1%97.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-6 — Про обрання Голови ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-6_%D0%BF%D1%80%D0%BE_%D0%BE%D0%B1%D1%80%D0%B0%D0%BD%D0%BD%D1%8F_%D0%93%D0%BE%D0%BB%D0%BE%D0%B2%D0%B8_%D0%A4%D0%9F%D0%A3.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-7 — Про внесення змін до Статуту ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-7__%D0%A1%D1%82%D0%B0%D1%82%D1%83%D1%82_%D0%A4%D0%9F%D0%A3.docx",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-8 — Про резолюції, заяви та звернення VII З'їзду ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/7%D0%B7-8.docx",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-9 — Про підтвердження повноважень нового складу Ради ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-9_%D1%87%D0%BB%D0%B5%D0%BD%D0%B8_%D0%A0%D0%B0%D0%B4%D0%B8.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-10 — Про обрання Контрольно-ревізійної комісії ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-10_%D0%BF%D1%80%D0%BE_%D0%9A%D0%A0%D0%9A.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-11 — Про обрання Статутної комісії ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/7з-11__Статутна_комісія.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
    {
        "title": "Постанова №7з-12 — Про підписання документів VII З'їзду ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2016/Zizd/"
                    "7%D0%B7-12_%D0%BF%D1%96%D0%B4%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%BD%D1%8F_%D0%B4%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D1%96%D0%B2.doc",
        "file_type": FileType.DOC,
        "published_at": datetime.date(2016, 3, 1),
    },
]

_VIII_ZJIZD = [
    {
        "title": "Постанова №8з-2 — Про Регламент VIII З'їзду ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/8з-2_Регламент_Зїзду.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
    {
        "title": "Постанова №8з-3 — Про Звіт Ради ФПУ за 2016–2021 рр.",
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/8з-3_Звіт_Ради_ФПУ.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
    {
        "title": "Постанова №8з-6 — Про обрання Голови ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/8з-6_Обрання_Голови_ФПУ.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
    {
        "title": "Постанова №8з-7 — Про зміни до Статуту ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/8з-7_Статут_ФПУ.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
    {
        "title": 'Постанова №8з-8 — Про Стратегію ФПУ на 2021–2026 «Час дій та якісних змін»',
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/"
                    "8з-8_Стратегія_діяльності_ФПУ_на_2021-2026_роки.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
    {
        "title": "Постанова №8з-9 — Про Заяву та Резолюцію VIII З'їзду ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/8з-9_заява_и_та_резолюція.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
    {
        "title": "Постанова №8з-13 — Про обрання Контрольно-ревізійної комісії ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/8з-13_склад_КРК.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
    {
        "title": "Постанова №8з-14 — Про підтвердження повноважень нового складу Ради ФПУ",
        "file_url": "https://www.fpsu.org.ua/images/images/2021/June/230621/"
                    "8з-14_склад_Ради_ФПУ_та_1_оргзасідання.pdf",
        "file_type": FileType.PDF,
        "published_at": datetime.date(2021, 6, 23),
    },
]

_GALUZEVI = [
    {
        "title": "Реєстр галузевих (міжгалузевих) угод",
        "file_url": "https://www.fpsu.org.ua/generalna-ugoda-galuzevi-ugodi-teritorialni-ugodi/"
                    "galuzevi-dogovori/526-reestr-galuzevikh-mizhgaluzevikh-ugod",
        "file_type": FileType.OTHER,
        "published_at": None,
    },
]

_GENERALNA = [
    {
        "title": "Генеральна угода про регулювання основних принципів і норм реалізації соціально-економічної політики і трудових відносин в Україні на 2019–2021 роки",
        "file_url": "https://www.fpsu.org.ua/generalna-ugoda-galuzevi-ugodi-teritorialni-ugodi/"
                    "generalnij-dogovir",
        "file_type": FileType.OTHER,
        "published_at": datetime.date(2019, 1, 1),
    },
]

_ZAKONODAVSTVO = [
    {
        "title": "Законодавство України (zakon.rada.gov.ua)",
        "file_url": "https://zakon.rada.gov.ua/laws",
        "file_type": FileType.OTHER,
        "published_at": None,
    },
    {
        "title": "Нормативно-правова база КМУ (kmu.gov.ua)",
        "file_url": "https://www.kmu.gov.ua/npas",
        "file_type": FileType.OTHER,
        "published_at": None,
    },
]

_STATIC_PAGE_SLUGS = {
    "postanovi-radi-fpu":      "/dokumenti-fpu/postanovi-radi-fpu",
    "postanovi-prezidiji-fpu": "/dokumenti-fpu/postanovi-prezidiji-fpu",
}

_HARDCODED: dict[str, list[dict]] = {
    "statut-fpu":                          _STATUT,
    "strategiya-diyalnosti-fpu-2021-2026": _STRATEGY,
    "reprezentativnist":                   _REPREZENT,
    "materialy-vii-zyizdu-fpu":            _VII_ZJIZD,
    "materialy-viii-zyizdu-fpu":           _VIII_ZJIZD,
    "galuzevi-ugodi":                      _GALUZEVI,
    "generalna-ugoda":                     _GENERALNA,
    "zakonodavstvo-pro-profspilky":        _ZAKONODAVSTVO,
}


class Command(BaseCommand):
    help = "Seed Document records for all DocumentCategory entries (idempotent)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing Document records before seeding.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        do_clear: bool = options["clear"]

        if do_clear and not dry_run:
            deleted, _ = Document.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing documents.")

        cats = {c.slug: c for c in DocumentCategory.objects.all()}
        total_created = 0
        total_updated = 0

        with transaction.atomic():
            for slug, cat in cats.items():
                items: list[dict] = []

                if slug in _STATIC_PAGE_SLUGS:
                    page_path = _STATIC_PAGE_SLUGS[slug]
                    try:
                        page = StaticPage.objects.get(url_path=page_path)
                        items = _parse_postanovy(page.body)
                    except StaticPage.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"  StaticPage not found: {page_path}")
                        )
                        continue
                elif slug in _HARDCODED:
                    items = _HARDCODED[slug]
                else:
                    self.stdout.write(self.style.WARNING(f"  No data source for slug={slug!r}"))
                    continue

                if not items:
                    self.stdout.write(f"  {slug}: 0 items parsed")
                    continue

                cat_created = 0
                cat_updated = 0

                if not dry_run:
                    for i, item in enumerate(items):
                        _, created = Document.objects.update_or_create(
                            category=cat,
                            file_url=item["file_url"],
                            defaults={
                                "title": item["title"],
                                "file_type": item["file_type"],
                                "published_at": item.get("published_at"),
                                "is_published": True,
                                "order": i,
                            },
                        )
                        if created:
                            cat_created += 1
                        else:
                            cat_updated += 1
                    total_created += cat_created
                    total_updated += cat_updated

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {slug}: {cat_created} created, {cat_updated} updated"
                    )
                    if not dry_run
                    else f"  [DRY] {slug}: {len(items)} documents would be seeded"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {total_created} created, {total_updated} updated."
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
