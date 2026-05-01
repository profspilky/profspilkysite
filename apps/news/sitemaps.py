"""Sitemaps for news articles and categories."""
from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from .models import Article, Category


class ArticleSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return Article.objects.filter(is_published=True).select_related("category")

    def location(self, obj: Article) -> str:
        return obj.get_absolute_url()

    def lastmod(self, obj: Article):
        return obj.published_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return Category.objects.filter(is_active=True).exclude(path="")

    def location(self, obj: Category) -> str:
        return f"/{obj.path}/"
