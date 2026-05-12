"""Core admin — SiteSettings (singleton), Priority, TeamMember, MemberOrganization."""
from __future__ import annotations

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import MemberOrganization, Priority, SiteSettings, TeamMember

admin.site.site_header = "Адмінпанель ФПУ"
admin.site.site_title = "ФПУ Admin"
admin.site.index_title = "Управління сайтом"


@admin.register(Priority)
class PriorityAdmin(ModelAdmin):
    list_display = ("title", "icon_key", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "icon_key")
    search_fields = ("title", "description")
    ordering = ("order",)
    list_per_page = 25


@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = ("get_photo_preview", "full_name", "role", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("full_name", "role", "bio")
    ordering = ("order",)
    readonly_fields = ("get_photo_preview",)
    list_per_page = 25

    fieldsets = (
        (None, {
            "fields": ("full_name", "role", "bio"),
        }),
        ("Фото", {
            "fields": ("get_photo_preview", "photo"),
        }),
        ("Відображення", {
            "fields": ("order", "is_active"),
        }),
    )

    @admin.display(description="Фото")
    def get_photo_preview(self, obj: TeamMember) -> str:
        url = obj.photo_url
        if url:
            return format_html(
                '<img src="{}" style="height:60px;width:60px;object-fit:cover;border-radius:50%;" />',
                url,
            )
        initials = obj.initials or "?"
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'height:60px;width:60px;border-radius:50%;background:#e5e7eb;'
            'font-weight:600;font-size:1.1rem;color:#374151;">{}</span>',
            initials,
        )


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
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

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.objects.first()
        if obj:
            return HttpResponseRedirect(
                reverse("admin:core_sitesettings_change", args=[obj.pk])
            )
        return HttpResponseRedirect(reverse("admin:core_sitesettings_add"))


@admin.register(MemberOrganization)
class MemberOrganizationAdmin(ModelAdmin):
    list_display = ("get_logo_preview", "name", "org_type", "region", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("org_type", "is_active")
    search_fields = ("name", "region")
    ordering = ("org_type", "order", "name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("get_logo_preview",)
    list_per_page = 50

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "org_type", "region"),
        }),
        ("Контакт", {
            "fields": ("website_url",),
        }),
        ("Логотип", {
            "fields": ("get_logo_preview", "logo"),
        }),
        ("Опис та відображення", {
            "fields": ("description", "order", "is_active"),
        }),
    )

    @admin.display(description="Логотип")
    def get_logo_preview(self, obj: MemberOrganization) -> str:
        if obj.logo:
            try:
                url = obj.logo.url
                return format_html(
                    '<img src="{}" style="height:48px;max-width:120px;object-fit:contain;" />',
                    url,
                )
            except Exception:
                pass
        return "—"
