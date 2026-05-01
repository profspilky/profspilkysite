"""Gallery views — album list and album detail with photos."""
from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import GalleryAlbum, GalleryPhoto


@require_GET
def album_list(request: HttpRequest) -> HttpResponse:
    """List of all published albums, paginated 24/page."""
    qs = GalleryAlbum.objects.filter(is_published=True).order_by("-event_date", "-created_at")
    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    canonical = request.build_absolute_uri("/gallery/")
    context = {
        "page_obj": page_obj,
        "page_meta_title": "Фотогалерея",
        "page_meta_description": "Фотогалерея Федерації профспілок України — фотозвіти заходів та подій.",
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "Фотогалерея", "url": "/gallery/"},
        ],
    }
    return render(request, "gallery/album_list.html", context)


@require_GET
def album_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Single album page with all photos for lightbox."""
    album = get_object_or_404(GalleryAlbum, slug=slug, is_published=True)
    photos = GalleryPhoto.objects.filter(album=album, is_published=True).order_by("order", "id")

    canonical = request.build_absolute_uri(album.get_absolute_url())
    context = {
        "album": album,
        "photos": photos,
        "page_meta_title": album.title,
        "page_meta_description": album.description[:160] if album.description else f"Фотоальбом «{album.title}» — Федерація профспілок України.",
        "canonical_url": canonical,
        "og_image": album.cover_url,
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "Фотогалерея", "url": "/gallery/"},
            {"title": album.title, "url": album.get_absolute_url()},
        ],
    }
    return render(request, "gallery/album_detail.html", context)
