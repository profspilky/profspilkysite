"""Documents models — official documents with file download."""
from __future__ import annotations

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class FileType(models.TextChoices):
    PDF = "pdf", "PDF"
    DOC = "doc", "DOC/DOCX"
    XLS = "xls", "XLS/XLSX"
    OTHER = "other", "Інше"


class DocumentCategory(models.Model):
    """Category for grouping documents (Постанови, Статут, etc.)."""

    title = models.CharField(_("Назва"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True, allow_unicode=True)
    description = models.TextField(_("Опис"), blank=True)
    order = models.PositiveSmallIntegerField(_("Порядок"), default=0)

    class Meta:
        verbose_name = _("Категорія документів")
        verbose_name_plural = _("Категорії документів")
        ordering = ("order", "title")

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.title, allow_unicode=False) or "docs"
            slug = base
            i = 2
            while DocumentCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        from django.urls import reverse
        return reverse("documents:category_detail", kwargs={"slug": self.slug})


class Document(models.Model):
    """Official document available for download."""

    title = models.CharField(_("Назва"), max_length=500)
    category = models.ForeignKey(
        DocumentCategory,
        verbose_name=_("Категорія"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    file = models.FileField(
        _("Файл"),
        upload_to="documents/%Y/",
        blank=True,
    )
    file_url = models.URLField(
        _("Зовнішнє URL"),
        blank=True,
        help_text=_("Якщо документ зберігається за зовнішнім URL"),
    )
    file_type = models.CharField(
        _("Тип файлу"),
        max_length=8,
        choices=FileType.choices,
        default=FileType.PDF,
    )
    description = models.TextField(_("Опис"), blank=True)
    published_at = models.DateField(_("Дата публікації"), null=True, blank=True)
    is_published = models.BooleanField(_("Опублікований"), default=True)
    order = models.PositiveSmallIntegerField(_("Порядок"), default=0)
    created_at = models.DateTimeField(_("Створено"), auto_now_add=True)

    class Meta:
        verbose_name = _("Документ")
        verbose_name_plural = _("Документи")
        ordering = ("-published_at", "-created_at", "order")
        indexes = [
            models.Index(fields=["category", "is_published"]),
            models.Index(fields=["-published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def download_url(self) -> str:
        if self.file:
            return self.file.url
        return self.file_url

    @property
    def file_ext(self) -> str:
        if self.file:
            name = self.file.name
            return name.rsplit(".", 1)[-1].upper() if "." in name else self.file_type.upper()
        return self.file_type.upper()
