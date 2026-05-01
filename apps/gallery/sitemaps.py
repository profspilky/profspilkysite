"""Gallery sitemaps."""
from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from .models import GalleryAlbum


class GalleryAlbumSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return GalleryAlbum.objects.filter(is_published=True)

    def lastmod(self, obj: GalleryAlbum):
        return obj.updated_at

    def location(self, obj: GalleryAlbum) -> str:
        return obj.get_absolute_url()
