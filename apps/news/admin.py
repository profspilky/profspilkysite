from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import Article, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "path", "joomla_id", "is_active", "article_count")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("title", "alias", "path")
    ordering = ("path",)

    def article_count(self, obj: Category) -> int:
        return obj.articles.filter(is_published=True).count()
    article_count.short_description = "Статей"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title", "category", "published_at", "is_published", "cover_preview"
    )
    list_filter = (
        "is_published",
        ("published_at", admin.DateFieldListFilter),
        "category",
    )
    list_editable = ("is_published",)
    search_fields = ("title", "summary", "joomla_id")
    date_hierarchy = "published_at"
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at",)
    raw_id_fields = ("category",)
    list_per_page = 50
    list_select_related = ("category",)
    readonly_fields = ("joomla_id", "cover_preview_large")

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "category", "published_at", "is_published"),
        }),
        ("Вміст", {
            "fields": ("summary", "body", "image", "cover_preview_large"),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Joomla (тільки читання)", {
            "fields": ("joomla_id",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Обкладинка")
    def cover_preview(self, obj: Article) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html('<img src="{}" alt="" height="40" style="border-radius:4px;">', url)

    @admin.display(description="Обкладинка")
    def cover_preview_large(self, obj: Article) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html('<img src="{}" alt="" style="max-height:160px;border-radius:8px;">', url)
