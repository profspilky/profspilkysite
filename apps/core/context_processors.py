"""Context processors used across all templates (header, footer, lang)."""
from __future__ import annotations

import datetime

from django.conf import settings
from django.core.cache import cache


def site_chrome(request):
    nav_items = [
        {
            "label": "Головна",
            "url": "/",
            "children": [],
        },
        {
            "label": "Про ФПУ",
            "url": "/pro-fpu",
            "children": [
                {"label": "Історія ФПУ",                          "url": "/pro-fpu/istoriya-fpu"},
                {"label": "Виборні органи ФПУ",                   "url": "/pro-fpu/viborchi-organi-fpu"},
                {"label": "Керівництво ФПУ",                      "url": "/pro-fpu/kerivnitstvo-fpu"},
                {"label": "Президія",                              "url": "/pro-fpu/prezidiya"},
                {"label": "Членські організації",                  "url": "/pro-fpu/chlenski-organizatsiji"},
                {"label": "Комісії ФПУ",                          "url": "/pro-fpu/komissii-fpu"},
                {"label": "Законодавче регулювання діяльності",   "url": "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok"},
                {"label": "Символіка ФПУ",                        "url": "/pro-fpu/simvolika-fpu"},
            ],
        },
        {
            "label": "Напрями діяльності",
            "url": "/napryamki-diyalnosti",
            "children": [
                {"label": "Правовий захист",                           "url": "/napryamki-diyalnosti/pravovij-zakhist"},
                {"label": "Охорона праці і здоров'я",                 "url": "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya"},
                {"label": "Соціальний захист",                         "url": "/napryamki-diyalnosti/sotsialnij-zakhist"},
                {"label": "Виробнича політика та ціноутворення",       "url": "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya"},
                {"label": "Соціальне страхування і пенсійне забезп.", "url": "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya"},
                {"label": "Соціальний діалог",                         "url": "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"},
                {"label": "Організаційна робота",                      "url": "/napryamki-diyalnosti/organizatsijna-robota"},
                {"label": "Молодіжна політика",                        "url": "/napryamki-diyalnosti/molodizhna-politika"},
                {"label": "Інформаційна робота",                       "url": "/napryamki-diyalnosti/informatsijna-robota"},
                {"label": "Міжнародна робота",                         "url": "/napryamki-diyalnosti/mizhnarodna-robota"},
            ],
        },
        {
            "label": "Документи ФПУ",
            "url": "/dokumenti-fpu",
            "children": [
                {"label": "Постанови Ради ФПУ",     "url": "/dokumenti-fpu/postanovi-radi-fpu"},
                {"label": "Постанови Президії ФПУ", "url": "/dokumenti-fpu/postanovi-prezidiji-fpu"},
                {"label": "Статут ФПУ",             "url": "/dokumenti-fpu/statut-fpu"},
            ],
        },
        {
            "label": "Контакти",
            "url": "/novi-kontakti-fpu",
            "children": [],
        },
        {
            "label": "Фотогалерея",
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

    return {
        "site_nav_items": nav_items,
        "site_languages": settings.LANGUAGES,
        "site_brand": "ФПУ",
        "site_year": datetime.date.today().year,
        "site_settings": site_settings,
    }
