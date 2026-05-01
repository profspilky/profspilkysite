from __future__ import annotations

from django.contrib import admin

from .models import MemberOrganization, Priority, SiteSettings, TeamMember

# ── Кастомізація заголовка адмінки ────────────────────────────────────────────
admin.site.site_header = "Адмінпанель ФПУ"
admin.site.site_title = "ФПУ Admin"
admin.site.index_title = "Управління сайтом"


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ("title", "icon_key", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "icon_key")
    search_fields = ("title", "description")
    ordering = ("order",)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("full_name", "role", "bio")
    ordering = ("order",)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Основне", {
            "fields": ("site_name", "tagline"),
        }),
        ("Контакти", {
            "fields": ("contact_phone", "hotline_phone", "contact_email", "address"),
        }),
        ("Соціальні мережі", {
            "fields": ("facebook_url", "youtube_url", "telegram_url"),
        }),
        ("Футер", {
            "fields": ("footer_text",),
        }),
    )

    def has_add_permission(self, request) -> bool:
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(MemberOrganization)
class MemberOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "region", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("org_type", "is_active")
    search_fields = ("name", "region")
    ordering = ("org_type", "order", "name")
    prepopulated_fields = {"slug": ("name",)}
