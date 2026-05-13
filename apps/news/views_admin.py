"""Admin-only helper views for the news editor."""
from __future__ import annotations

import cloudinary.uploader
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@require_POST
def upload_image(request: HttpRequest) -> JsonResponse:
    """Upload an inline image to Cloudinary and return its secure URL.

    This view is registered via ArticleAdmin.get_urls() and wrapped with
    admin_site.admin_view(), which enforces login + staff checks automatically.
    """
    image = request.FILES.get("image")
    if not image:
        return JsonResponse({"error": "Файл не передано"}, status=400)

    if image.content_type not in _ALLOWED_CONTENT_TYPES:
        return JsonResponse(
            {"error": "Дозволені формати: JPEG, PNG, GIF, WebP"}, status=400
        )

    if image.size > _MAX_SIZE_BYTES:
        return JsonResponse(
            {"error": "Файл завеликий — максимум 10 МБ"}, status=400
        )

    result = cloudinary.uploader.upload(
        image,
        folder="fpsu/articles",
        resource_type="image",
        use_filename=True,
        unique_filename=True,
    )

    return JsonResponse({"url": result["secure_url"]})
