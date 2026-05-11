"""Pages views — static menu pages and standalone root-level articles."""
from __future__ import annotations

import re

from django.http import Http404, HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from apps.core.nav import NAV_SECTIONS
from apps.news.models import Article
from .models import StaticPage

# Стара Joomla транслітерувала «ї» як «ji»:
#   «України» → «krajini», «Федерації» → «federatsiji»
# Нові посилання іноді пишуться без «j» («kraini»).
# Патерн: «j» між голосними [aeou] + [i] — ознака «ї» → «ji».
_JI_RE = re.compile(r"(?<=[aeou])i")


def _find_page_ji_fallback(url_html: str, url_plain: str) -> StaticPage | None:
    """Fallback: вставляємо 'j' за Joomla-патерном і шукаємо знову."""
    for url in (url_html, url_plain):
        variant = _JI_RE.sub("ji", url)
        if variant == url:
            continue
        try:
            return StaticPage.objects.get(url_path=variant, is_published=True)
        except StaticPage.DoesNotExist:
            pass
    return None

# Breadcrumb lookup побудований з NAV_SECTIONS (єдине джерело навігації).
_URL_CRUMB: dict[str, list[dict]] = {}

for _section in NAV_SECTIONS:
    _surl = _section["url"].rstrip("/")
    _URL_CRUMB[_surl] = [
        {"title": _("Головна"), "url": "/"},
        {"title": _section["label"], "url": _section["url"]},
    ]
    for _child in _section.get("children", []):
        _curl = _child["url"].rstrip("/")
        _URL_CRUMB[_curl] = [
            {"title": _("Головна"), "url": "/"},
            {"title": _section["label"], "url": _section["url"]},
            {"title": _child["label"], "url": _child["url"]},
        ]


def _build_breadcrumbs(url_path: str) -> list[dict]:
    """Return breadcrumb list for a StaticPage url_path."""
    clean = url_path.rstrip("/").removesuffix(".html")
    crumbs = _URL_CRUMB.get(clean)
    if crumbs:
        return crumbs

    segments = [s for s in clean.split("/") if s]
    result: list[dict] = [{"title": _("Головна"), "url": "/"}]
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

    context = {
        "page": page,
        "breadcrumbs": breadcrumbs,
        "recent_articles": recent_articles,
        "page_meta_title": page.effective_meta_title,
        "page_meta_description": page.meta_description,
        "page_meta_keywords": page.meta_keywords,
        "canonical_url": canonical,
    }
    return render(request, "pages/static_page.html", context)


@require_GET
def static_page(request: HttpRequest, path: str) -> HttpResponse:
    """Static menu page accessed with .html suffix: /<path>.html"""
    url_path_html = f"/{path}.html"
    url_path_plain = f"/{path}"
    try:
        page = StaticPage.objects.get(url_path=url_path_html, is_published=True)
    except StaticPage.DoesNotExist:
        # Fallback: ji-транслітерація
        page = _find_page_ji_fallback(url_path_html, url_path_plain)
        if page is None:
            page = get_object_or_404(StaticPage, url_path=url_path_html, is_published=True)
        else:
            # 301 на канонічний URL (без .html)
            canonical_path = page.url_path.removesuffix(".html")
            return HttpResponsePermanentRedirect(canonical_path)
    return _render_static(request, page)


@require_GET
def static_page_no_ext(request: HttpRequest, path: str) -> HttpResponse:
    """Static menu page without .html: /<path>"""
    url_path_html = f"/{path}.html"
    url_path_plain = f"/{path}"
    try:
        page = StaticPage.objects.get(url_path=url_path_html, is_published=True)
    except StaticPage.DoesNotExist:
        try:
            page = StaticPage.objects.get(url_path=url_path_plain, is_published=True)
        except StaticPage.DoesNotExist:
            # Fallback: ji-транслітерація — 301 на канонічний URL
            page = _find_page_ji_fallback(url_path_html, url_path_plain)
            if page is None:
                raise Http404
            canonical_path = page.url_path.removesuffix(".html")
            return HttpResponsePermanentRedirect(canonical_path)
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
            "breadcrumbs": [{"title": _("Головна"), "url": "/"}],
        }
        return render(request, "news/article_detail.html", context)
    except Article.DoesNotExist:
        pass

    url_path = f"/{joomla_id}-{slug}.html"
    page = get_object_or_404(StaticPage, url_path=url_path, is_published=True)
    return _render_static(request, page)
