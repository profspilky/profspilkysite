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
            {"label": _("Історія ФПУ"),                                       "url": "/pro-fpu/istoriya-fpu/"},
            {"label": _("Виборні органи ФПУ"),                                "url": "/pro-fpu/viborchi-organi-fpu/"},
            {"label": _("Керівництво ФПУ"),                                   "url": "/pro-fpu/kerivnitstvo-fpu/"},
            {"label": _("Президія"),                                           "url": "/pro-fpu/prezidiya/"},
            {"label": _("Членські організації"),                               "url": "/pro-fpu/chlenski-organizatsiji/"},
            {"label": _("Комісії ФПУ"),                                       "url": "/pro-fpu/komissii-fpu/"},
            {"label": _("Законодавче регулювання діяльності профспілок"),     "url": "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok/"},
            {"label": _("Символіка ФПУ"),                                     "url": "/pro-fpu/simvolika-fpu/"},
            {"label": _("Профспілкові відзнаки"),                             "url": "/pro-fpu/profspilkovi-vidznaki/"},
        ],
    },
    {
        "label": _("Напрями діяльності"),
        "url": "/napryamki-diyalnosti/",
        "children": [
            {"label": _("Правовий захист"),                                         "url": "/napryamki-diyalnosti/pravovij-zakhist/"},
            {"label": _("Охорона праці і здоров'я"),                               "url": "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya/"},
            {"label": _("Соціальний захист"),                                       "url": "/napryamki-diyalnosti/sotsialnij-zakhist/"},
            {"label": _("Виробнича політика та ціноутворення"),                     "url": "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya/"},
            {"label": _("Соціальне страхування і пенсійне забезпечення"),           "url": "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya/"},
            {"label": _("Соціальний діалог та колективно-договірне регулювання"),   "url": "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya/"},
            {"label": _("Організаційна робота"),                                    "url": "/napryamki-diyalnosti/organizatsijna-robota/"},
            {"label": _("Молодіжна політика"),                                      "url": "/napryamki-diyalnosti/molodizhna-politika/"},
            {"label": _("Інформаційна робота"),                                     "url": "/napryamki-diyalnosti/informatsijna-robota/"},
            {"label": _("Міжнародна робота"),                                       "url": "/napryamki-diyalnosti/mizhnarodna-robota/"},
            {"label": _("Наш навчальний заклад — АПСВТ"),                          "url": "/napryamki-diyalnosti/navchalnyi-zaklad-apsvt/"},
        ],
    },
    {
        "label": _("Документи ФПУ"),
        "url": "/documents/",
        "children": [
            {"label": _("Матеріали VII З'їзду ФПУ"),                 "url": "/documents/materiali-vii-zizdu-fpu/"},
            {"label": _("Матеріали VIII З'їзду ФПУ"),                "url": "/documents/materiali-viii-zizdu-fpu/"},
            {"label": _("Постанови Ради ФПУ"),                       "url": "/documents/postanovi-radi-fpu/"},
            {"label": _("Постанови Президії ФПУ"),                   "url": "/documents/postanovi-prezidiji-fpu/"},
            {"label": _("Статут ФПУ"),                               "url": "/documents/statut-fpu/"},
            {"label": _("Стратегія діяльності ФПУ на 2021–2026"),    "url": "/documents/strategiya-diyalnosti-fpu/"},
            {"label": _("Репрезентативність"),                       "url": "/documents/reprezentativnist/"},
        ],
    },
    {
        "label": _("Контакти"),
        "url": "/contacts/",
        "children": [],
    },
    {
        "label": _("Сайти членських організацій"),
        "url": "/sajty-chlenskykh-orhanizatsii/",
        "children": [],
    },
    {
        "label": _("Стратегія діяльності ФПУ"),
        "url": "/documents/strategiya-diyalnosti-fpu/",
        "children": [],
    },
    {
        "label": _("Фотовиставка"),
        "url": "/gallery/",
        "children": [],
    },
    {
        "label": _("СПО об'єднань профспілок"),
        "url": "/spo-ob-iednan-profspilok/",
        "children": [],
    },
]
