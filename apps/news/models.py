"""News models — Category and Article, images stored in Cloudinary."""
from __future__ import annotations

from cloudinary.models import CloudinaryField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Joomla category mirror — one row per content category."""

    joomla_id = models.IntegerField(_("Joomla ID"), unique=True, null=True, blank=True)
    alias = models.SlugField(_("Alias"), max_length=400, unique=True, allow_unicode=True)
    title = models.CharField(_("Назва"), max_length=255)
    path = models.CharField(
        _("URL-шлях"),
        max_length=400,
        blank=True,
        help_text=_("Наприклад: materialy або pro-fpu/istoriya"),
    )
    meta_description = models.CharField(_("Meta description"), max_length=1024, blank=True)
    meta_keywords = models.CharField(_("Meta keywords"), max_length=1024, blank=True)
    is_active = models.BooleanField(_("Активна"), default=True)

    class Meta:
        verbose_name = _("Категорія")
        verbose_name_plural = _("Категорії")
        ordering = ("path", "title")
        indexes = [
            models.Index(fields=["path"]),
            models.Index(fields=["alias"]),
        ]

    def __str__(self) -> str:
        return self.title


class Article(models.Model):
    """News article — each article maps to a Joomla content item."""

    # Django-native fields
    title = models.CharField(_("Заголовок"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=400, unique=True, blank=True, allow_unicode=True)
    summary = models.CharField(_("Короткий опис"), max_length=500, blank=True)
    body = models.TextField(_("Повний текст"), blank=True)
    image = CloudinaryField(_("Зображення"), blank=True, null=True)
    local_image = models.CharField(
        _("Локальне зображення"),
        max_length=500,
        blank=True,
        help_text=_("Відносний шлях у media/joomla_images/, напр. images/foo.webp"),
    )
    published_at = models.DateTimeField(_("Дата публікації"), default=timezone.now)
    is_published = models.BooleanField(_("Опубліковано"), default=True)
    order = models.IntegerField(_("Ручний порядок"), default=0)

    # Joomla migration fields
    joomla_id = models.IntegerField(_("Joomla ID"), unique=True, null=True, blank=True, db_index=True)
    category = models.ForeignKey(
        Category,
        verbose_name=_("Категорія"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    # SEO fields (from Joomla metadesc/metakey + custom page title)
    meta_title = models.CharField(
        _("SEO заголовок (title)"),
        max_length=255,
        blank=True,
        help_text=_("Якщо порожньо — використовується поле Заголовок"),
    )
    meta_description = models.CharField(
        _("Meta description"),
        max_length=500,
        blank=True,
    )
    meta_keywords = models.CharField(
        _("Meta keywords"),
        max_length=500,
        blank=True,
    )

    class Meta:
        verbose_name = _("Новина")
        verbose_name_plural = _("Новини")
        ordering = ("-published_at", "-id")
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["joomla_id"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.title, allow_unicode=False) or "article"
            slug = base
            i = 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def effective_meta_title(self) -> str:
        return self.meta_title or self.title

    @property
    def display_date(self) -> str:
        return self.published_at.strftime("%d.%m.%Y")

    @property
    def image_url(self) -> str:
        if self.image:
            try:
                return self.image.url
            except Exception:
                pass
        if self.local_image:
            return f"/media/joomla_images/{self.local_image}"
        # Fallback: extract first inline image from body HTML
        if self.body:
            import re as _re
            m = _re.search(
                r'src="(https?://(?:www\.)?fpsu\.org\.ua/images/[^"]+)"',
                self.body,
            )
            if m:
                return m.group(1)
        return ""

    def get_absolute_url(self) -> str:
        """Return the Joomla-compatible URL for this article."""
        if self.category and self.category.path:
            return f"/{self.category.path}/{self.joomla_id}-{self.slug}.html"
        if self.joomla_id:
            return f"/{self.joomla_id}-{self.slug}.html"
        # Fallback для статей без joomla_id (наприклад, нові статті)
        return f"/news/{self.slug}/"
