"""Core admin — SiteSettings (singleton), Priority, TeamMember, MemberOrganization, PageSection, MemOrgPage."""
from __future__ import annotations

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import ContactMessage, MemOrgPage, MemberOrganization, PageSection, Priority, SiteSettings, TeamMember

admin.site.site_header = "Адмінпанель ФПУ"
admin.site.site_title = "ФПУ Admin"
admin.site.index_title = "Управління сайтом"


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ("created_at", "name", "email", "subject_short", "is_read")
    list_editable = ("is_read",)
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "ip_address", "created_at")
    ordering = ("-created_at",)
    list_per_page = 50
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {
            "fields": ("created_at", "is_read"),
        }),
        ("Відправник", {
            "fields": ("name", "email", "ip_address"),
        }),
        ("Повідомлення", {
            "fields": ("subject", "message"),
        }),
    )

    def has_add_permission(self, request) -> bool:
        return False

    @admin.display(description="Тема")
    def subject_short(self, obj: ContactMessage) -> str:
        return obj.subject[:70] + "…" if len(obj.subject) > 70 else obj.subject


@admin.register(Priority)
class PriorityAdmin(ModelAdmin):
    list_display = ("title", "icon_key", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "icon_key")
    search_fields = ("title", "description")
    ordering = ("order",)
    list_per_page = 25

    fieldsets = (
        (None, {
            "fields": ("title", "icon_key", "description"),
        }),
        ("Відображення", {
            "fields": ("order", "is_active"),
        }),
    )


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
        ("Кнопка «Написати нам»", {
            "fields": ("write_us_label", "write_us_url"),
            "description": "CTA-кнопка у шапці сайту поруч з логотипом. "
                           "Залиште текст порожнім, щоб повністю приховати кнопку.",
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


@admin.register(MemOrgPage)
class MemOrgPageAdmin(ModelAdmin):
    list_display = ("title", "short_name", "org_type", "region", "founded_year", "has_website", "is_published")
    list_editable = ("is_published",)
    list_filter = ("org_type", "is_published")
    search_fields = ("title", "short_name", "region", "address", "email")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("source_url",)
    list_per_page = 50

    fieldsets = (
        (None, {
            "fields": ("title", "short_name", "slug", "org_type", "region"),
        }),
        ("Зміст", {
            "fields": ("description", "meta_description"),
        }),
        ("Контакти", {
            "fields": ("address", "phone", "email", "founded_year", "website_url"),
        }),
        ("Логотип та джерело", {
            "fields": ("logo", "source_url"),
        }),
        ("Відображення", {
            "fields": ("is_published",),
        }),
    )

    @admin.display(description="Власний сайт", boolean=True)
    def has_website(self, obj: MemOrgPage) -> bool:
        return bool(obj.website_url)


@admin.register(PageSection)
class PageSectionAdmin(ModelAdmin):
    list_display = ("__str__", "page", "section_type", "title_short", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("page", "section_type", "is_active")
    ordering = ("page", "order")
    readonly_fields = ("get_image_preview",)
    list_per_page = 30

    fieldsets = (
        ("Розміщення", {
            "fields": ("page", "section_type", "order", "is_active"),
        }),
        ("Контент", {
            "fields": ("title", "subtitle", "body"),
            "description": "Заголовок і підзаголовок відображаються на сторінці. "
                           "Повний текст — опціонально для блоків із детальним описом.",
        }),
        ("Кнопка / посилання", {
            "fields": ("link_text", "link_url"),
        }),
        ("Фонове зображення", {
            "fields": ("get_image_preview", "image"),
        }),
    )

    @admin.display(description="Заголовок")
    def title_short(self, obj: PageSection) -> str:
        return obj.title[:60] + "…" if len(obj.title) > 60 else obj.title or "—"

    @admin.display(description="Поточне зображення")
    def get_image_preview(self, obj: PageSection) -> str:
        url = obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="max-height:120px;max-width:100%;border-radius:8px;" />',
                url,
            )
        return "—"
