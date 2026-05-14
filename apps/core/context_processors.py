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


def _is_nav_active(url: str, path: str) -> bool:
    """Return True if the given nav URL matches the current request path."""
    if url == "/":
        return path in ("/", "")
    return path == url or path.startswith(url)


def site_chrome(request):
    current_path = _strip_lang_prefix(request.path)

    raw_items = [
        {"label": _("Головна"), "url": "/", "children": []},
        *NAV_SECTIONS,
    ]

    # #region agent log
    import json as _j, time as _t
    try:
        napryamky = next((i for i in raw_items if "/napryamki" in i.get("url", "")), None)
        with open("/Users/olegbonislavskyi/Sites/Профспілки/.cursor/debug-8dffc0.log", "a") as _f:
            _f.write(_j.dumps({"sessionId": "8dffc0", "timestamp": int(_t.time() * 1000), "location": "context_processors.py:site_chrome", "message": "nav children for Напрями", "data": {"count": len(napryamky["children"]) if napryamky else 0, "labels": [c["label"] for c in napryamky["children"]] if napryamky else []}, "hypothesisId": "H4_H5", "runId": "run2"}) + "\n")
    except Exception as _e:
        pass
    # #endregion
    nav_items = []
    for item in raw_items:
        children_with_active = [
            {**child, "is_active": _is_nav_active(child["url"], current_path)}
            for child in item.get("children", [])
        ]
        is_active = _is_nav_active(item["url"], current_path) or any(
            c["is_active"] for c in children_with_active
        )
        nav_items.append({**item, "children": children_with_active, "is_active": is_active})

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
