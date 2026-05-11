"""Context processors used across all templates (header, footer, lang)."""
from __future__ import annotations

import datetime

from django.conf import settings
from django.core.cache import cache

from django.utils.translation import gettext_lazy as _

from apps.core.nav import NAV_SECTIONS


def _strip_lang_prefix(path: str) -> str:
    """Return path without language prefix (e.g. '/en/gallery/' → '/gallery/').

    Only non-default languages carry a URL prefix when prefix_default_language=False.
    Strips the first matching prefix so translate_url() can resolve the path
    regardless of which language is currently active.
    """
    for code, _ in settings.LANGUAGES:
        prefix = f"/{code}/"
        if path.startswith(prefix):
            return path[len(f"/{code}"):]
    return path


def site_chrome(request):
    nav_items = [
        {
            "label": _("Головна"),
            "url": "/",
            "children": [],
        },
        *NAV_SECTIONS,
        {
            "label": _("Фотогалерея"),
            "url": "/gallery/",
            "children": [],
        },
    ]

    # SiteSettings — кешуємо на 5 хв, щоб не бити в БД на кожен запит
    site_settings = cache.get("site_settings")
    if site_settings is None:
        try:
            from apps.core.models import SiteSettings
            site_settings = SiteSettings.get()
            cache.set("site_settings", site_settings, 300)
        except Exception:
            site_settings = None

    # Пріоритети — панель є на кожній сторінці через base.html
    priorities = cache.get("site_priorities")
    if priorities is None:
        try:
            from apps.core.models import Priority
            from apps.core.utils import default_priorities
            priorities = list(Priority.objects.filter(is_active=True).order_by("order"))
            if not priorities:
                priorities = default_priorities()
            cache.set("site_priorities", priorities, 300)
        except Exception:
            from apps.core.utils import default_priorities
            priorities = default_priorities()

    return {
        "site_nav_items": nav_items,
        "site_languages": settings.LANGUAGES,
        "site_brand": "ФПУ",
        "site_year": datetime.date.today().year,
        "site_settings": site_settings,
        "priorities": priorities,
        "lang_switch_next": _strip_lang_prefix(request.path),
    }
