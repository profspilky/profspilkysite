"""Core views — home, search, contact."""
from __future__ import annotations

from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.models import Priority, SiteSettings, TeamMember
from apps.core.utils import default_articles, default_priorities, default_team_members
from apps.news.models import Article
from apps.pages.models import StaticPage


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    articles_qs = (
        Article.objects.filter(is_published=True)
        .select_related("category")
        .order_by("-published_at")[:10]
    )
    articles = list(articles_qs)
    if not articles:
        articles = default_articles()

    priorities_qs = Priority.objects.filter(is_active=True).order_by("order")
    priorities = list(priorities_qs)
    if not priorities:
        priorities = default_priorities()

    team_qs = TeamMember.objects.filter(is_active=True).order_by("order")
    team_members = list(team_qs) or default_team_members()

    # Прев'ю галереї (останні 6 альбомів)
    gallery_preview = []
    try:
        from apps.gallery.models import GalleryAlbum
        gallery_preview = list(
            GalleryAlbum.objects.filter(is_published=True)
            .order_by("-event_date", "-created_at")[:6]
        )
    except Exception:
        pass

    context = {
        "articles": articles,
        "priorities": priorities,
        "team_members": team_members,
        "gallery_preview": gallery_preview,
    }
    return render(request, "core/home.html", context)


@require_GET
def search(request: HttpRequest) -> HttpResponse:
    """Full-text search across articles and static pages."""
    query = request.GET.get("q", "").strip()
    page_num = request.GET.get("page", 1)
    results = []
    total = 0

    if query:
        article_qs = (
            Article.objects.filter(is_published=True)
            .filter(
                Q(title__icontains=query)
                | Q(summary__icontains=query)
                | Q(body__icontains=query)
            )
            .order_by("-published_at")
            .select_related("category")
        )
        page_qs = (
            StaticPage.objects.filter(is_published=True)
            .filter(Q(title__icontains=query) | Q(body__icontains=query))
        )

        # Об'єднуємо результати (articles пріоритетніші)
        combined = list(article_qs[:100]) + list(page_qs[:20])
        total = len(combined)
        paginator = Paginator(combined, 20)
        results = paginator.get_page(page_num)

    canonical = request.build_absolute_uri("/search/")
    context = {
        "query": query,
        "results": results,
        "total": total,
        "page_meta_title": f"Пошук: {query}" if query else "Пошук",
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "Пошук", "url": "/search/"},
        ],
    }
    return render(request, "core/search.html", context)


@require_http_methods(["GET", "POST"])
def contact(request: HttpRequest) -> HttpResponse:
    """Contact form — sends email via SMTP."""
    settings_obj = SiteSettings.get()
    success = False
    errors: dict[str, str] = {}
    form_data: dict = {}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        # Проста валідація
        if not name:
            errors["name"] = "Введіть ваше ім'я"
        if not email or "@" not in email:
            errors["email"] = "Введіть коректний email"
        if not subject:
            errors["subject"] = "Введіть тему"
        if not message or len(message) < 10:
            errors["message"] = "Повідомлення надто коротке"

        form_data = {"name": name, "email": email, "subject": subject, "message": message}

        if not errors:
            # Rate limit — простий cache-based (5 запитів/год з IP)
            ip = request.META.get("REMOTE_ADDR", "unknown")
            from django.core.cache import cache as django_cache
            rate_key = f"contact_rate_{ip}"
            count = django_cache.get(rate_key, 0)
            if count >= 5:
                errors["__all__"] = "Забагато запитів. Спробуйте пізніше."
            else:
                django_cache.set(rate_key, count + 1, 3600)
                try:
                    send_mail(
                        subject=f"[ФПУ] {subject} — від {name}",
                        message=f"Від: {name} <{email}>\n\n{message}",
                        from_email=settings_obj.contact_email or "noreply@fpsu.org.ua",
                        recipient_list=[settings_obj.contact_email or "fpsu@fpsu.org.ua"],
                        fail_silently=False,
                    )
                    success = True
                    form_data = {}
                except Exception:
                    errors["__all__"] = "Помилка відправки. Спробуйте пізніше або зателефонуйте."

    canonical = request.build_absolute_uri("/contacts/")
    context = {
        "success": success,
        "errors": errors,
        "form_general_error": errors.get("__all__", ""),
        "form_data": form_data,
        "site_settings": settings_obj,
        "page_meta_title": "Контакти",
        "page_meta_description": "Контакти Федерації профспілок України: адреса, телефон, форма зворотного зв'язку.",
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "Контакти", "url": "/contacts/"},
        ],
    }
    return render(request, "core/contact.html", context)
