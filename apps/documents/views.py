"""Documents views — category list and document listing."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Document, DocumentCategory


@require_GET
def document_index(request: HttpRequest) -> HttpResponse:
    """All document categories."""
    categories = DocumentCategory.objects.prefetch_related("documents").order_by("order", "title")
    canonical = request.build_absolute_uri("/documents/")
    context = {
        "categories": categories,
        "page_meta_title": "Документи ФПУ",
        "page_meta_description": "Офіційні документи Федерації профспілок України: постанови, угоди, статут.",
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "Документи ФПУ", "url": "/documents/"},
        ],
    }
    return render(request, "documents/document_index.html", context)


@require_GET
def category_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Documents in a category."""
    category = get_object_or_404(DocumentCategory, slug=slug)
    documents = Document.objects.filter(category=category, is_published=True).order_by("order", "-published_at")
    canonical = request.build_absolute_uri(category.get_absolute_url())
    context = {
        "category": category,
        "documents": documents,
        "page_meta_title": category.title,
        "page_meta_description": category.description[:160] or f"Документи категорії «{category.title}» — ФПУ",
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "Документи ФПУ", "url": "/documents/"},
            {"title": category.title, "url": category.get_absolute_url()},
        ],
    }
    return render(request, "documents/category_detail.html", context)
