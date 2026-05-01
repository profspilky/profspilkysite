"""Gallery models — albums and photos stored in Cloudinary."""
from __future__ import annotations

from cloudinary.models import CloudinaryField
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class GalleryAlbum(models.Model):
    """Photo album — each album maps to a JoomGallery category."""

    joomla_id = models.IntegerField(_("Joomla ID"), unique=True, null=True, blank=True)
    title = models.CharField(_("Назва"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=300, unique=True, allow_unicode=True)
    description = models.TextField(_("Опис"), blank=True)
    event_date = models.DateField(_("Дата заходу"), null=True, blank=True)
    cover_image = CloudinaryField(_("Обкладинка"), blank=True, null=True)
    cover_local = models.CharField(
        _("Локальна обкладинка"),
        max_length=500,
        blank=True,
        help_text=_("Шлях у media/joomla_images/"),
    )
    is_published = models.BooleanField(_("Опублікований"), default=True)
    created_at = models.DateTimeField(_("Створено"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Оновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Альбом")
        verbose_name_plural = _("Альбоми")
        ordering = ("-event_date", "-created_at")
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_published", "-event_date"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.title, allow_unicode=False) or "album"
            slug = base
            i = 2
            while GalleryAlbum.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        from django.urls import reverse
        return reverse("gallery:album_detail", kwargs={"slug": self.slug})

    @property
    def cover_url(self) -> str:
        if self.cover_image:
            try:
                return self.cover_image.url
            except Exception:
                pass
        if self.cover_local:
            return f"/media/joomla_images/{self.cover_local}"
        return ""

    @property
    def photo_count(self) -> int:
        return self.photos.filter(is_published=True).count()


class GalleryPhoto(models.Model):
    """Single photo inside an album."""

    joomla_id = models.IntegerField(_("Joomla ID"), null=True, blank=True)
    album = models.ForeignKey(
        GalleryAlbum,
        verbose_name=_("Альбом"),
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = CloudinaryField(_("Фото"), blank=True, null=True)
    image_local = models.CharField(
        _("Локальний шлях"),
        max_length=500,
        blank=True,
        help_text=_("Відносний шлях у media/joomla_images/"),
    )
    title = models.CharField(_("Підпис"), max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(_("Порядок"), default=0)
    is_published = models.BooleanField(_("Опублікована"), default=True)

    class Meta:
        verbose_name = _("Фото")
        verbose_name_plural = _("Фотографії")
        ordering = ("order", "id")
        indexes = [
            models.Index(fields=["album", "is_published", "order"]),
        ]

    def __str__(self) -> str:
        return self.title or f"Фото #{self.pk}"

    @property
    def image_url(self) -> str:
        if self.image:
            try:
                return self.image.url
            except Exception:
                pass
        if self.image_local:
            return f"/media/joomla_images/{self.image_local}"
        return ""
