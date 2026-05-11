"""Project URL configuration."""
from __future__ import annotations

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView

from apps.news.sitemaps import ArticleSitemap, CategorySitemap
from apps.pages.sitemaps import StaticPageSitemap
from apps.gallery.sitemaps import GalleryAlbumSitemap


def healthz(_request: object) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


def robots_txt(_request: object) -> HttpResponse:
    content = "\n".join([
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        f"Sitemap: https://{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'www.fpsu.org.ua'}/sitemap.xml",
    ])
    return HttpResponse(content, content_type="text/plain")


SITEMAPS = {
    "articles": ArticleSitemap,
    "categories": CategorySitemap,
    "pages": StaticPageSitemap,
    "gallery": GalleryAlbumSitemap,
}

urlpatterns = [
    # Redirect /admin (no slash) → /admin/ before pages catch-all intercepts it
    path("admin", RedirectView.as_view(url="/admin/", permanent=True)),
    path("healthz/", healthz, name="healthz"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

urlpatterns += i18n_patterns(
    path("", include("apps.core.urls")),
    path(_("login/"), include("apps.accounts.urls")),
    # Gallery URLs before news (more specific)
    path("", include("apps.gallery.urls")),
    # Documents URLs
    path("", include("apps.documents.urls")),
    # News URLs must come before pages — more specific patterns first
    path("", include("apps.news.urls")),
    # Pages: stub nav pages + Joomla static/standalone pages (catch-all last)
    path("", include("apps.pages.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
