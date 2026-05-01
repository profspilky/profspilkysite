"""Documents admin."""
from django.contrib import admin

from .models import Document, DocumentCategory


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    fields = ("title", "file", "file_type", "published_at", "order", "is_published")
    show_change_link = True


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "order", "doc_count")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [DocumentInline]

    def doc_count(self, obj: DocumentCategory) -> int:
        return obj.documents.filter(is_published=True).count()
    doc_count.short_description = "Документів"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "file_type", "published_at", "is_published")
    list_filter = ("category", "file_type", "is_published")
    search_fields = ("title", "description")
    date_hierarchy = "published_at"
    list_select_related = ("category",)
