"""Gallery admin — albums with inline photos."""
from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryAlbum, GalleryPhoto


class GalleryPhotoInline(admin.TabularInline):
    model = GalleryPhoto
    extra = 0
    fields = ("image", "image_local", "title", "order", "is_published")
    readonly_fields = ("preview",)

    def preview(self, obj: GalleryPhoto) -> str:
        url = obj.image_url
        if url:
            return format_html('<img src="{}" style="height:60px;border-radius:4px;">', url)
        return "—"
    preview.short_description = "Прев'ю"


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = ("title", "event_date", "photo_count_display", "is_published", "created_at")
    list_filter = ("is_published", "event_date")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "event_date"
    inlines = [GalleryPhotoInline]
    readonly_fields = ("cover_preview",)

    def photo_count_display(self, obj: GalleryAlbum) -> int:
        return obj.photos.filter(is_published=True).count()
    photo_count_display.short_description = "Фото"

    def cover_preview(self, obj: GalleryAlbum) -> str:
        url = obj.cover_url
        if url:
            return format_html('<img src="{}" style="height:100px;border-radius:8px;">', url)
        return "—"
    cover_preview.short_description = "Обкладинка"


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "album", "order", "is_published")
    list_filter = ("album", "is_published")
    search_fields = ("title",)
    list_select_related = ("album",)
