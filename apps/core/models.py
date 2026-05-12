"""Core models — site-wide configurable content."""
from __future__ import annotations

from cloudinary.models import CloudinaryField
from django.db import models
from django.utils.translation import gettext_lazy as _


class SectionPage(models.TextChoices):
    HOME = "home", _("Головна сторінка")
    ABOUT = "about", _("Про ФПУ")
    CONTACTS = "contacts", _("Контакти")
    GALLERY = "gallery", _("Галерея")
    DOCUMENTS = "documents", _("Документи")
    SPO = "spo", _("СПО")


class SectionType(models.TextChoices):
    HERO = "hero", _("Hero-банер")
    ANNOUNCE = "announce", _("Оголошення-рядок")
    PROMO = "promo", _("Промо-блок")
    CTA = "cta", _("Заклик до дії")


class PageSection(models.Model):
    """Editable content block for a key page — block constructor."""

    page = models.CharField(
        _("Сторінка"), max_length=20, choices=SectionPage.choices, default=SectionPage.HOME
    )
    section_type = models.CharField(
        _("Тип блоку"), max_length=20, choices=SectionType.choices, default=SectionType.HERO
    )
    title = models.CharField(_("Заголовок"), max_length=300, blank=True)
    subtitle = models.CharField(_("Підзаголовок / опис"), max_length=600, blank=True)
    body = models.TextField(_("Повний текст"), blank=True)
    link_text = models.CharField(_("Текст кнопки"), max_length=120, blank=True)
    link_url = models.CharField(
        _("URL кнопки"),
        max_length=500,
        blank=True,
        help_text=_("Відносний /про-фпу/ або повний https://…"),
    )
    image = CloudinaryField(_("Фонове зображення"), blank=True, null=True)
    order = models.PositiveSmallIntegerField(_("Порядок"), default=0)
    is_active = models.BooleanField(_("Активний"), default=True)

    class Meta:
        verbose_name = _("Блок сторінки")
        verbose_name_plural = _("Конструктор сторінок")
        ordering = ("page", "order", "id")

    def __str__(self) -> str:
        return f"{self.get_page_display()} — {self.get_section_type_display()}"

    @property
    def image_url(self) -> str:
        if self.image:
            try:
                return self.image.url
            except Exception:
                return ""
        return ""


class SiteSettings(models.Model):
    """Singleton — global site configuration (contacts, socials, footer text)."""

    site_name = models.CharField(_("Назва сайту"), max_length=120, default="Федерація профспілок України")
    tagline = models.CharField(_("Слоган"), max_length=240, blank=True)
    contact_phone = models.CharField(_("Телефон"), max_length=40, blank=True, default="+380 44 355-77-90")
    hotline_phone = models.CharField(_("Гаряча лінія"), max_length=40, blank=True, default="+380 67 199-27-26")
    contact_email = models.EmailField(_("Email"), blank=True, default="fpsu@fpsu.org.ua")
    address = models.CharField(
        _("Адреса"),
        max_length=300,
        blank=True,
        default="01024, м. Київ, майдан Незалежності, 2 (Будинок Профспілок)",
    )
    facebook_url = models.URLField(_("Facebook"), blank=True)
    youtube_url = models.URLField(_("YouTube"), blank=True)
    telegram_url = models.URLField(_("Telegram"), blank=True)
    footer_text = models.TextField(_("Текст футера"), blank=True)

    class Meta:
        verbose_name = _("Налаштування сайту")
        verbose_name_plural = _("Налаштування сайту")

    def __str__(self) -> str:
        return self.site_name

    @classmethod
    def get(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class OrgType(models.TextChoices):
    SECTORAL = "sectoral", _("Всеукраїнська галузева")
    REGIONAL = "regional", _("Територіальне об'єднання")


class PriorityIcon(models.TextChoices):
    SHIELD = "shield", _("Щит (захист прав)")
    HARD_HAT = "hard_hat", _("Каска (безпека праці)")
    DIALOG = "dialog", _("Діалог")
    HEART = "heart", _("Серце (допомога)")


class Priority(models.Model):
    """One card in the «Наші Пріоритети» panel."""

    icon_key = models.CharField(
        _("Іконка"),
        max_length=32,
        choices=PriorityIcon.choices,
        default=PriorityIcon.SHIELD,
    )
    title = models.CharField(_("Заголовок"), max_length=120)
    description = models.CharField(_("Опис"), max_length=240, blank=True)
    order = models.PositiveSmallIntegerField(_("Порядок"), default=0)
    is_active = models.BooleanField(_("Активний"), default=True)

    class Meta:
        verbose_name = _("Пріоритет")
        verbose_name_plural = _("Пріоритети")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title


class TeamMember(models.Model):
    """One person in the «Наша команда» section."""

    full_name = models.CharField(_("Повне імʼя"), max_length=120)
    role = models.CharField(_("Посада"), max_length=160)
    bio = models.CharField(_("Короткий опис"), max_length=300, blank=True)
    photo = CloudinaryField(_("Фото"), blank=True, null=True)
    order = models.PositiveSmallIntegerField(_("Порядок"), default=0)
    is_active = models.BooleanField(_("Активний"), default=True)

    class Meta:
        verbose_name = _("Член команди")
        verbose_name_plural = _("Команда")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.full_name

    @property
    def photo_url(self) -> str:
        if self.photo:
            try:
                return self.photo.url
            except Exception:
                return ""
        return ""

    @property
    def initials(self) -> str:
        parts = self.full_name.split()
        return "".join(p[0].upper() for p in parts[:2] if p)


class MemberOrganization(models.Model):
    """Member union organization — sectoral or regional."""

    org_type = models.CharField(
        _("Тип"),
        max_length=12,
        choices=OrgType.choices,
        default=OrgType.SECTORAL,
    )
    name = models.CharField(_("Назва"), max_length=500)
    slug = models.SlugField(_("Slug"), max_length=300, unique=True, allow_unicode=True, blank=True)
    region = models.CharField(_("Регіон"), max_length=100, blank=True)
    website_url = models.URLField(_("Сайт"), blank=True)
    logo = CloudinaryField(_("Логотип"), blank=True, null=True)
    description = models.TextField(_("Опис"), blank=True)
    order = models.PositiveSmallIntegerField(_("Порядок"), default=0)
    is_active = models.BooleanField(_("Активна"), default=True)

    class Meta:
        verbose_name = _("Членська організація")
        verbose_name_plural = _("Членські організації")
        ordering = ("order", "name")

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name, allow_unicode=False) or f"org-{self.pk or 0}"
            slug = base[:280]
            i = 2
            while MemberOrganization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base[:270]}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
