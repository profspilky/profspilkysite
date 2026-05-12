"""Gallery admin — albums with inline photos, cover and photo previews."""
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import GalleryAlbum, GalleryPhoto


class GalleryPhotoInline(TabularInline):
    model = GalleryPhoto
    extra = 0
    fields = ("get_preview", "image", "image_local", "title", "order", "is_published")
    readonly_fields = ("get_preview",)

    @admin.display(description="Прев'ю")
    def get_preview(self, obj: GalleryPhoto) -> str:
        url = obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="height:56px;width:80px;object-fit:cover;border-radius:4px;" />',
                url,
            )
        return "—"


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(ModelAdmin):
    list_display = (
        "get_cover_preview",
        "title",
        "event_date",
        "get_photo_count",
        "is_published",
    )
    list_filter = ("is_published",)
    list_editable = ("is_published",)
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [GalleryPhotoInline]
    readonly_fields = ("get_cover_preview_large",)
    list_per_page = 30

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "description", "event_date", "is_published"),
        }),
        ("Обкладинка", {
            "fields": ("get_cover_preview_large", "cover_image", "cover_local"),
        }),
        ("Joomla", {
            "fields": ("joomla_id",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="")
    def get_cover_preview(self, obj: GalleryAlbum) -> str:
        url = obj.cover_url
        if url:
            return format_html(
                '<img src="{}" style="height:44px;width:66px;object-fit:cover;border-radius:4px;" />',
                url,
            )
        return "—"

    @admin.display(description="Поточна обкладинка")
    def get_cover_preview_large(self, obj: GalleryAlbum) -> str:
        url = obj.cover_url
        if url:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:100%;border-radius:8px;" />',
                url,
            )
        return "—"

    @admin.display(description="Фото")
    def get_photo_count(self, obj: GalleryAlbum) -> int:
        return obj.photos.filter(is_published=True).count()


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(ModelAdmin):
    list_display = ("get_image_preview", "__str__", "album", "order", "is_published")
    list_filter = ("album", "is_published")
    list_editable = ("order", "is_published")
    search_fields = ("title",)
    list_select_related = ("album",)
    readonly_fields = ("get_image_preview",)
    list_per_page = 50

    fieldsets = (
        (None, {
            "fields": ("album", "title", "order", "is_published"),
        }),
        ("Зображення", {
            "fields": ("get_image_preview", "image", "image_local"),
        }),
        ("Joomla", {
            "fields": ("joomla_id",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="")
    def get_image_preview(self, obj: GalleryPhoto) -> str:
        url = obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="height:60px;width:90px;object-fit:cover;border-radius:4px;" />',
                url,
            )
        return "—"
