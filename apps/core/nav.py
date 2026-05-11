"""Shared navigation sections — single source of truth.

Used by both `apps.core.context_processors` (header nav) and
`apps.pages.views` (breadcrumb generation).
"""
from django.utils.translation import gettext_lazy as _

NAV_SECTIONS: list[dict] = [
    {
        "label": _("Про ФПУ"),
        "url": "/pro-fpu/",
        "children": [
            {"label": _("Історія ФПУ"),                        "url": "/pro-fpu/istoriya-fpu/"},
            {"label": _("Виборні органи ФПУ"),                 "url": "/pro-fpu/viborchi-organi-fpu/"},
            {"label": _("Керівництво ФПУ"),                    "url": "/pro-fpu/kerivnitstvo-fpu/"},
            {"label": _("Президія"),                            "url": "/pro-fpu/prezidiya/"},
            {"label": _("Членські організації"),                "url": "/pro-fpu/chlenski-organizatsiji/"},
            {"label": _("Комісії ФПУ"),                        "url": "/pro-fpu/komissii-fpu/"},
            {"label": _("Законодавче регулювання діяльності"), "url": "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok/"},
            {"label": _("Символіка ФПУ"),                      "url": "/pro-fpu/simvolika-fpu/"},
        ],
    },
    {
        "label": _("Напрями діяльності"),
        "url": "/napryamki-diyalnosti/",
        "children": [
            {"label": _("Правовий захист"),                          "url": "/napryamki-diyalnosti/pravovij-zakhist/"},
            {"label": _("Охорона праці і здоров'я"),                "url": "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya/"},
            {"label": _("Соціальний захист"),                        "url": "/napryamki-diyalnosti/sotsialnij-zakhist/"},
            {"label": _("Виробнича політика та ціноутворення"),      "url": "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya/"},
            {"label": _("Соціальне страхування і пенсійне забезп."), "url": "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya/"},
            {"label": _("Соціальний діалог"),                        "url": "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya/"},
            {"label": _("Організаційна робота"),                     "url": "/napryamki-diyalnosti/organizatsijna-robota/"},
            {"label": _("Молодіжна політика"),                       "url": "/napryamki-diyalnosti/molodizhna-politika/"},
            {"label": _("Інформаційна робота"),                      "url": "/napryamki-diyalnosti/informatsijna-robota/"},
            {"label": _("Міжнародна робота"),                        "url": "/napryamki-diyalnosti/mizhnarodna-robota/"},
        ],
    },
    {
        "label": _("Документи ФПУ"),
        "url": "/dokumenti-fpu/",
        "children": [
            {"label": _("Постанови Ради ФПУ"),     "url": "/dokumenti-fpu/postanovi-radi-fpu/"},
            {"label": _("Постанови Президії ФПУ"), "url": "/dokumenti-fpu/postanovi-prezidiji-fpu/"},
            {"label": _("Статут ФПУ"),             "url": "/dokumenti-fpu/statut-fpu/"},
        ],
    },
    {
        "label": _("Контакти"),
        "url": "/contacts/",
        "children": [],
    },
]
