"""Reusable helpers for the home page.

`default_priorities` and `default_articles` provide content for first run,
when admin hasn't filled the database yet — so the homepage always looks
populated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from django.utils.translation import gettext_lazy as _

from apps.core.models import PriorityIcon


@dataclass(frozen=True)
class FallbackPriority:
    icon_key: str
    title: str
    description: str = ""

    def __str__(self) -> str:
        return self.title


@dataclass(frozen=True)
class FallbackArticle:
    title: str
    summary: str
    published_at: date
    image_url: str = ""
    slug: str = "#"

    @property
    def display_date(self) -> str:
        return self.published_at.strftime("%d.%m.%Y")

    def get_absolute_url(self) -> str:
        return "#"


def default_priorities() -> list[FallbackPriority]:
    return [
        FallbackPriority(PriorityIcon.SHIELD, str(_("Правовий Захист"))),
        FallbackPriority(PriorityIcon.HARD_HAT, str(_("Безпека Праці"))),
        FallbackPriority(PriorityIcon.DIALOG, str(_("Соціальний Діалог"))),
        FallbackPriority(PriorityIcon.HEART, str(_("Як Ми Допомагаємо"))),
    ]


def default_articles() -> list[FallbackArticle]:
    return [
        FallbackArticle(
            title=str(_("ФПУ Відстоює Права Медиків")),
            summary=str(_("Колективні переговори щодо умов праці медичних працівників.")),
            published_at=date(2024, 5, 27),
        ),
        FallbackArticle(
            title=str(_("Новий Колективний Договір в Обороні")),
            summary=str(_("Підписано новий галузевий договір для працівників оборонної сфери.")),
            published_at=date(2024, 5, 22),
        ),
        FallbackArticle(
            title=str(_("Соціальний Діалог: Підсумки Кварталу")),
            summary=str(_("Щоквартальні підсумки взаємодії з роботодавцями та урядом.")),
            published_at=date(2024, 5, 21),
        ),
        FallbackArticle(
            title=str(_("Федерація Профспілок України на Міжнародному Форумі")),
            summary=str(_("Делегація ФПУ взяла участь у щорічній зустрічі європейських профспілок.")),
            published_at=date(2024, 5, 21),
        ),
        FallbackArticle(
            title=str(_("Підтримка Працівників Освіти")),
            summary=str(_("Програма матеріальної допомоги педагогам у складних регіонах.")),
            published_at=date(2024, 5, 18),
        ),
        FallbackArticle(
            title=str(_("Захист Працівників Транспорту")),
            summary=str(_("Звернення до уряду щодо умов праці та оплати водіїв громадського транспорту.")),
            published_at=date(2024, 5, 14),
        ),
    ]


@dataclass(frozen=True)
class FallbackTeamMember:
    full_name: str
    role: str
    bio: str = ""
    photo_url: str = ""

    @property
    def initials(self) -> str:
        parts = self.full_name.split()
        return "".join(p[0].upper() for p in parts[:2] if p)


def default_team_members() -> list[FallbackTeamMember]:
    return [
        FallbackTeamMember(
            full_name=str(_("Григорій Осовий")),
            role=str(_("Голова Федерації Профспілок України")),
        ),
        FallbackTeamMember(
            full_name=str(_("Катерина Бондаренко")),
            role=str(_("Заступник Голови")),
        ),
        FallbackTeamMember(
            full_name=str(_("Олексій Мірошниченко")),
            role=str(_("Керівник правового відділу")),
        ),
        FallbackTeamMember(
            full_name=str(_("Тетяна Коваль")),
            role=str(_("Начальник відділу охорони праці")),
        ),
        FallbackTeamMember(
            full_name=str(_("Сергій Захаренко")),
            role=str(_("Директор з міжнародних відносин")),
        ),
        FallbackTeamMember(
            full_name=str(_("Оксана Петренко")),
            role=str(_("Прес-секретар ФПУ")),
        ),
    ]


def chunks(items: Iterable, size: int) -> list[list]:
    """Split iterable into fixed-size chunks (used in templates)."""
    items = list(items)
    return [items[i : i + size] for i in range(0, len(items), size)]
