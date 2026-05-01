"""CMS static pages — mirrors Joomla menu/article pages."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class StaticPage(models.Model):
    """A static content page sourced from Joomla menu or standalone article."""

    url_path = models.CharField(
        _("URL-шлях"),
        max_length=500,
        unique=True,
        help_text=_("Наприклад: /pro-fpu/istoriya-fpu або /276-cherhovyi-den.html"),
    )
    title = models.CharField(_("Заголовок"), max_length=255)
    meta_title = models.CharField(
        _("SEO заголовок"),
        max_length=255,
        blank=True,
        help_text=_("Якщо порожньо — використовується Заголовок"),
    )
    meta_description = models.CharField(_("Meta description"), max_length=500, blank=True)
    meta_keywords = models.CharField(_("Meta keywords"), max_length=500, blank=True)
    body = models.TextField(_("Вміст сторінки"), blank=True)
    is_published = models.BooleanField(_("Опублікована"), default=True)

    # Joomla reference
    joomla_id = models.IntegerField(_("Joomla menu/article ID"), null=True, blank=True)
    joomla_type = models.CharField(
        _("Тип Joomla"),
        max_length=50,
        blank=True,
        help_text=_("menu | article"),
    )

    class Meta:
        verbose_name = _("Статична сторінка")
        verbose_name_plural = _("Статичні сторінки")
        ordering = ("url_path",)
        indexes = [models.Index(fields=["url_path"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.url_path})"

    @property
    def effective_meta_title(self) -> str:
        return self.meta_title or self.title
