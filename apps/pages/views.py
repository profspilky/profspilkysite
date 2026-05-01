"""Pages views — static menu pages and standalone root-level articles."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.core.models import Priority
from apps.news.models import Article
from .models import StaticPage

# Navigation tree mirroring context_processors.site_chrome — used for
# breadcrumb generation without an extra DB query.
_NAV_TREE: list[dict] = [
    {
        "label": "Про ФПУ",
        "url": "/pro-fpu",
        "children": [
            {"label": "Історія ФПУ",                         "url": "/pro-fpu/istoriya-fpu"},
            {"label": "Виборні органи ФПУ",                  "url": "/pro-fpu/viborchi-organi-fpu"},
            {"label": "Керівництво ФПУ",                     "url": "/pro-fpu/kerivnitstvo-fpu"},
            {"label": "Президія",                            "url": "/pro-fpu/prezidiya"},
            {"label": "Членські організації",                "url": "/pro-fpu/chlenski-organizatsiji"},
            {"label": "Комісії ФПУ",                         "url": "/pro-fpu/komissii-fpu"},
            {"label": "Законодавче регулювання діяльності",  "url": "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok"},
            {"label": "Символіка ФПУ",                       "url": "/pro-fpu/simvolika-fpu"},
        ],
    },
    {
        "label": "Напрями діяльності",
        "url": "/napryamki-diyalnosti",
        "children": [
            {"label": "Правовий захист",                          "url": "/napryamki-diyalnosti/pravovij-zakhist"},
            {"label": "Охорона праці і здоров'я",                "url": "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya"},
            {"label": "Соціальний захист",                        "url": "/napryamki-diyalnosti/sotsialnij-zakhist"},
            {"label": "Виробнича політика та ціноутворення",      "url": "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya"},
            {"label": "Соціальне страхування і пенсійне забезп.", "url": "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya"},
            {"label": "Соціальний діалог",                        "url": "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"},
            {"label": "Організаційна робота",                     "url": "/napryamki-diyalnosti/organizatsijna-robota"},
            {"label": "Молодіжна політика",                       "url": "/napryamki-diyalnosti/molodizhna-politika"},
            {"label": "Інформаційна робота",                      "url": "/napryamki-diyalnosti/informatsijna-robota"},
            {"label": "Міжнародна робота",                        "url": "/napryamki-diyalnosti/mizhnarodna-robota"},
        ],
    },
    {
        "label": "Документи ФПУ",
        "url": "/dokumenti-fpu",
        "children": [
            {"label": "Постанови Ради ФПУ",    "url": "/dokumenti-fpu/postanovi-radi-fpu"},
            {"label": "Постанови Президії ФПУ","url": "/dokumenti-fpu/postanovi-prezidiji-fpu"},
            {"label": "Статут ФПУ",            "url": "/dokumenti-fpu/statut-fpu"},
        ],
    },
    {
        "label": "Контакти",
        "url": "/novi-kontakti-fpu",
        "children": [],
    },
]

# Build a lookup: canonical url → (section_label, section_url, child_label)
# Used by _build_breadcrumbs for O(1) lookups.
_URL_CRUMB: dict[str, list[dict]] = {}

for _section in _NAV_TREE:
    _surl = _section["url"].rstrip("/")
    _URL_CRUMB[_surl] = [
        {"title": "Головна", "url": "/"},
        {"title": _section["label"], "url": _section["url"]},
    ]
    for _child in _section.get("children", []):
        _curl = _child["url"].rstrip("/")
        _URL_CRUMB[_curl] = [
            {"title": "Головна", "url": "/"},
            {"title": _section["label"], "url": _section["url"]},
            {"title": _child["label"], "url": _child["url"]},
        ]


def _build_breadcrumbs(url_path: str) -> list[dict]:
    """
    Return breadcrumb list for a StaticPage url_path.

    Checks the pre-built lookup first; falls back to splitting the path into
    segments so any nested page gets reasonable breadcrumbs.
    """
    clean = url_path.rstrip("/").rstrip(".html")
    crumbs = _URL_CRUMB.get(clean)
    if crumbs:
        return crumbs

    # Fallback: parse path segments
    segments = [s for s in clean.split("/") if s]
    result: list[dict] = [{"title": "Головна", "url": "/"}]
    accumulated = ""
    for seg in segments:
        accumulated += f"/{seg}"
        known = _URL_CRUMB.get(accumulated)
        if known:
            result = known[:]
        else:
            result.append({"title": seg.replace("-", " ").title(), "url": accumulated})
    return result


def _render_static(request: HttpRequest, page: StaticPage) -> HttpResponse:
    canonical = request.build_absolute_uri(page.url_path)
    breadcrumbs = _build_breadcrumbs(page.url_path)
    recent_articles = (
        Article.objects.filter(is_published=True)
        .order_by("-published_at")
        .only("title", "slug", "published_at", "joomla_id", "category_id")[:5]
    )
    priorities = Priority.objects.filter(is_active=True).order_by("order")

    context = {
        "page": page,
        "breadcrumbs": breadcrumbs,
        "recent_articles": recent_articles,
        "priorities": priorities,
        "page_meta_title": page.effective_meta_title,
        "page_meta_description": page.meta_description,
        "page_meta_keywords": page.meta_keywords,
        "canonical_url": canonical,
    }
    return render(request, "pages/static_page.html", context)


@require_GET
def static_page(request: HttpRequest, path: str) -> HttpResponse:
    """Static menu page accessed with .html suffix: /<path>.html"""
    url_path = f"/{path}.html"
    page = get_object_or_404(StaticPage, url_path=url_path, is_published=True)
    return _render_static(request, page)


@require_GET
def static_page_no_ext(request: HttpRequest, path: str) -> HttpResponse:
    """Static menu page without .html: /<path>"""
    url_path_html = f"/{path}.html"
    url_path_plain = f"/{path}"
    try:
        page = StaticPage.objects.get(url_path=url_path_html, is_published=True)
    except StaticPage.DoesNotExist:
        page = get_object_or_404(StaticPage, url_path=url_path_plain, is_published=True)
    return _render_static(request, page)


@require_GET
def standalone_page(
    request: HttpRequest,
    joomla_id: str,
    slug: str,
) -> HttpResponse:
    """Root-level Joomla article: /<joomla_id>-<slug>.html"""
    try:
        article = Article.objects.get(joomla_id=int(joomla_id), is_published=True)
        canonical = request.build_absolute_uri(article.get_absolute_url())
        context = {
            "article": article,
            "page_meta_title": article.effective_meta_title,
            "page_meta_description": article.meta_description,
            "page_meta_keywords": article.meta_keywords,
            "canonical_url": canonical,
            "og_image": article.image_url,
            "og_type": "article",
            "breadcrumbs": [{"title": "Головна", "url": "/"}],
        }
        return render(request, "news/article_detail.html", context)
    except Article.DoesNotExist:
        pass

    url_path = f"/{joomla_id}-{slug}.html"
    page = get_object_or_404(StaticPage, url_path=url_path, is_published=True)
    return _render_static(request, page)
