"""Core views — home, search, contact, joomla legacy redirects."""
from __future__ import annotations

from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.models import PageSection, Priority, SiteSettings, TeamMember
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

    home_sections = {
        s.section_type: s
        for s in PageSection.objects.filter(page="home", is_active=True).order_by("order")
    }

    spo_articles = list(
        Article.objects.filter(is_published=True)
        .filter(
            Q(category__alias__icontains="spo")
            | Q(category__path__icontains="spo")
            | Q(category__title__icontains="СПО")
        )
        .select_related("category")
        .order_by("-published_at")[:5]
    )

    context = {
        "articles": articles,
        "priorities": priorities,
        "team_members": team_members,
        "spo_articles": spo_articles,
        "hero_section": home_sections.get("hero"),
        "announce_section": home_sections.get("announce"),
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
        "page_meta_title": (_("Пошук") + f": {query}") if query else _("Пошук"),
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Пошук"), "url": "/search/"},
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
            errors["name"] = _("Введіть ваше ім'я")
        if not email or "@" not in email:
            errors["email"] = _("Введіть коректний email")
        if not subject:
            errors["subject"] = _("Введіть тему")
        if not message or len(message) < 10:
            errors["message"] = _("Повідомлення надто коротке")

        form_data = {"name": name, "email": email, "subject": subject, "message": message}

        if not errors:
            # Rate limit — простий cache-based (5 запитів/год з IP)
            ip = request.META.get("REMOTE_ADDR", "unknown")
            from django.core.cache import cache as django_cache
            rate_key = f"contact_rate_{ip}"
            count = django_cache.get(rate_key, 0)
            if count >= 5:
                errors["__all__"] = _("Забагато запитів. Спробуйте пізніше.")
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
                    errors["__all__"] = _("Помилка відправки. Спробуйте пізніше або зателефонуйте.")

    canonical = request.build_absolute_uri("/contacts/")
    context = {
        "success": success,
        "errors": errors,
        "form_general_error": errors.get("__all__", ""),
        "form_data": form_data,
        "site_settings": settings_obj,
        "page_meta_title": _("Контакти"),
        "page_meta_description": _("Контакти Федерації профспілок України: адреса, телефон, форма зворотного зв'язку."),
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Контакти"), "url": "/contacts/"},
        ],
    }
    return render(request, "core/contact.html", context)


@require_GET
def spo_page(request: HttpRequest) -> HttpResponse:
    """СПО об'єднань профспілок — section page."""
    # #region agent log
    import json as _j, time as _t
    try:
        with open("/Users/olegbonislavskyi/Sites/Профспілки/.cursor/debug-fd6f8e.log","a") as _f:
            _f.write(_j.dumps({"sessionId":"fd6f8e","timestamp":int(_t.time()*1000),"location":"core/views.py:spo_page","message":"spo_page view reached","data":{"path":request.path},"hypothesisId":"FIX","runId":"post-fix-v2"}) + "\n")
    except Exception: pass
    # #endregion
    from apps.documents.models import Document, DocumentCategory

    spo_articles = list(
        Article.objects.filter(is_published=True)
        .filter(
            Q(category__alias__icontains="spo")
            | Q(category__path__icontains="spo")
            | Q(category__title__icontains="СПО")
        )
        .select_related("category")
        .order_by("-published_at")[:20]
    )

    spo_doc_categories = list(
        DocumentCategory.objects.filter(title__icontains="СПО").order_by("order")
    )
    spo_docs = list(
        Document.objects.filter(
            is_published=True,
            category__in=spo_doc_categories,
        ).order_by("-published_at", "-created_at")[:10]
    ) if spo_doc_categories else []

    context = {
        "spo_articles": spo_articles,
        "spo_docs": spo_docs,
        "page_meta_title": "СПО об'єднань профспілок",
        "page_meta_description": (
            "Матеріали та рішення Спільного представницького органу "
            "сторони профспілок у Національній тристоронній соціально-економічній раді."
        ),
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "СПО об'єднань профспілок", "url": "/spo-obiednan-profspilok"},
        ],
    }
    return render(request, "core/spo.html", context)


@require_GET
def joomla_redirect(request: HttpRequest) -> HttpResponsePermanentRedirect:
    """301-редирект для старих Joomla index.php URL.

    Підтримувані формати:
      ?option=com_content&view=article&id=118:rada&catid=...  → article
      ?option=com_content&view=category&...&id=<catid>        → homepage fallback
      ?option=com_search&...                                   → /search/
      ?option=com_contact&...                                  → /contacts/
      все інше                                                 → /
    """
    params = request.GET
    option = params.get("option", "")
    view   = params.get("view", "")

    # ── com_search → search page ──────────────────────────────────────────────
    if option == "com_search":
        q = params.get("searchword", params.get("q", ""))
        return HttpResponsePermanentRedirect(f"/search/?q={q}" if q else "/search/")

    # ── com_contact → contacts page ───────────────────────────────────────────
    if option == "com_contact":
        return HttpResponsePermanentRedirect("/contacts/")

    # ── com_content, view=article ─────────────────────────────────────────────
    if option == "com_content" and view == "article":
        raw_id = params.get("id", "")
        joomla_id = _parse_joomla_id(raw_id)
        if joomla_id:
            try:
                article = Article.objects.get(joomla_id=joomla_id, is_published=True)
                return HttpResponsePermanentRedirect(article.get_absolute_url())
            except Article.DoesNotExist:
                pass
            # Спробуємо StaticPage по joomla_id у url_path
            try:
                page = StaticPage.objects.filter(
                    url_path__contains=f"{joomla_id}-"
                ).first()
                if page:
                    return HttpResponsePermanentRedirect(page.url_path.removesuffix(".html"))
            except Exception:
                pass

    # ── com_content, view=category → спробуємо знайти по префіксу шляху ──────
    if option == "com_content" and view in ("category", "section"):
        prefix = _path_prefix(request.path)
        if prefix:
            page = StaticPage.objects.filter(
                url_path__startswith=prefix, is_published=True
            ).first()
            if page:
                url = page.url_path.replace(".html", "")
                return HttpResponsePermanentRedirect(url)

    # ── fallback — homepage ───────────────────────────────────────────────────
    return HttpResponsePermanentRedirect("/")


def _parse_joomla_id(raw: str) -> int | None:
    """Parse joomla_id from '118:rada', '118-rada' or '118'."""
    if not raw:
        return None
    for sep in (":", "-"):
        if sep in raw:
            try:
                return int(raw.split(sep)[0])
            except ValueError:
                return None
    try:
        return int(raw)
    except ValueError:
        return None


def _path_prefix(path: str) -> str:
    """Return leading section from path, e.g. '/pro-fpu/index.php' → '/pro-fpu'."""
    parts = [p for p in path.rstrip("/").split("/") if p and p != "index.php"]
    return "/" + "/".join(parts) if parts else ""
