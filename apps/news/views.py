"""News views — article detail and category listing."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from .models import Article, Category


@require_GET
def article_in_cat(
    request: HttpRequest,
    cat_path: str,
    joomla_id: str,
    slug: str,
) -> HttpResponse:
    """Article accessed via /<cat_path>/<joomla_id>-<slug>.html."""
    article = get_object_or_404(
        Article,
        joomla_id=int(joomla_id),
        is_published=True,
    )
    # Note: slug mismatch is allowed — the canonical URL in <head> ensures
    # search engines treat the correct URL as authoritative.

    category = article.category
    canonical = request.build_absolute_uri(article.get_absolute_url())

    context = {
        "article": article,
        "category": category,
        "page_meta_title": article.effective_meta_title,
        "page_meta_description": article.meta_description,
        "page_meta_keywords": article.meta_keywords,
        "canonical_url": canonical,
        "og_image": article.image_url,
        "og_type": "article",
        "breadcrumbs": _build_breadcrumbs(category),
    }
    return render(request, "news/article_detail.html", context)


@require_GET
def category_list(request: HttpRequest, cat_path: str) -> HttpResponse:
    """Category listing page: /<cat_path>/"""
    category = get_object_or_404(Category, path=cat_path.strip("/"), is_active=True)
    articles = (
        Article.objects.filter(category=category, is_published=True)
        .order_by("-published_at")
        .select_related("category")[:50]
    )
    canonical = request.build_absolute_uri(f"/{cat_path}/")

    context = {
        "category": category,
        "articles": articles,
        "page_meta_title": category.title,
        "page_meta_description": category.meta_description,
        "page_meta_keywords": category.meta_keywords,
        "canonical_url": canonical,
    }
    return render(request, "news/category_list.html", context)


@require_GET
def article_by_slug(request: HttpRequest, slug: str) -> HttpResponse:
    """Article accessed via /news/<slug>/ — for articles without a Joomla ID."""
    article = get_object_or_404(Article, slug=slug, is_published=True)
    category = article.category
    canonical = request.build_absolute_uri(article.get_absolute_url())

    context = {
        "article": article,
        "category": category,
        "page_meta_title": article.effective_meta_title,
        "page_meta_description": article.meta_description,
        "page_meta_keywords": article.meta_keywords,
        "canonical_url": canonical,
        "og_image": article.image_url,
        "og_type": "article",
        "breadcrumbs": _build_breadcrumbs(category),
    }
    return render(request, "news/article_detail.html", context)


def _build_breadcrumbs(category: Category | None) -> list[dict]:
    crumbs: list[dict] = [{"title": _("Головна"), "url": "/"}]
    if category:
        crumbs.append({"title": category.title, "url": f"/{category.path}/"})
    return crumbs
