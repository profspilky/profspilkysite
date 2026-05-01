from __future__ import annotations

from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET


@require_GET
def login_stub(request):
    return render(request, "pages/stub.html", {"page_title": _("Увійти")})
