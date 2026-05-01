"""Sitemap for static CMS pages."""
from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from .models import StaticPage


class StaticPageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    protocol = "https"

    def items(self):
        return StaticPage.objects.filter(is_published=True)

    def location(self, obj: StaticPage) -> str:
        return obj.url_path
