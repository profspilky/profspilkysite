"""News admin — Category and Article with image previews."""
from __future__ import annotations

from django.contrib import admin
from django.urls import path
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from . import views_admin
from .forms import ArticleAdminForm
from .models import Article, Category


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("title", "path", "article_count", "joomla_id", "is_active")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("title", "alias", "path")
    ordering = ("path",)
    list_per_page = 50

    fieldsets = (
        (None, {
            "fields": ("title", "alias", "path", "is_active"),
        }),
        ("SEO", {
            "fields": ("meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Joomla", {
            "fields": ("joomla_id",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Статей")
    def article_count(self, obj: Category) -> int:
        return obj.articles.filter(is_published=True).count()


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    form = ArticleAdminForm

    def get_urls(self):
        custom = [
            path(
                "upload-image/",
                self.admin_site.admin_view(views_admin.upload_image),
                name="news_article_upload_image",
            ),
        ]
        return custom + super().get_urls()

    list_display = (
        "get_cover_preview",
        "title",
        "category",
        "published_at",
        "is_published",
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
    autocomplete_fields = ("category",)
    list_per_page = 50
    list_select_related = ("category",)
    readonly_fields = ("joomla_id", "get_cover_preview_large")

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "category", "published_at", "is_published"),
        }),
        ("Вміст", {
            "fields": ("summary", "body"),
        }),
        ("Зображення", {
            "fields": ("get_cover_preview_large", "image", "local_image"),
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

    @admin.display(description="")
    def get_cover_preview(self, obj: Article) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:44px;width:66px;object-fit:cover;border-radius:4px;" />',
            url,
        )

    @admin.display(description="Поточне зображення")
    def get_cover_preview_large(self, obj: Article) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-height:200px;max-width:100%;border-radius:8px;" />',
            url,
        )
