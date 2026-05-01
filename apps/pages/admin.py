from __future__ import annotations

from django.contrib import admin

from .models import StaticPage


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("title", "url_path", "is_published", "joomla_type")
    list_filter = ("is_published", "joomla_type")
    list_editable = ("is_published",)
    search_fields = ("title", "url_path")
    ordering = ("url_path",)
    list_per_page = 100

    fieldsets = (
        (None, {
            "fields": ("url_path", "title", "is_published"),
        }),
        ("Вміст", {
            "fields": ("body",),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Joomla (readonly)", {
            "fields": ("joomla_id", "joomla_type"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("joomla_id", "joomla_type")
