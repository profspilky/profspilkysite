"""Pages URL patterns — Joomla SEF static and standalone pages.

Patterns (in priority order):
  /<id>-<slug>.html  → standalone root-level article
  /<path>.html       → static menu page  (e.g. /pro-fpu/istoriya-fpu.html)
  /<path>            → static menu page without .html suffix (e.g. /pro-fpu)
"""
from __future__ import annotations

from django.urls import re_path

from . import views

app_name = "pages"

urlpatterns = [
    # Standalone root-level article: /<joomla_id>-<slug>.html
    re_path(
        r"^(?P<joomla_id>\d+)-(?P<slug>[\w-]+)\.html$",
        views.standalone_page,
        name="standalone_page",
    ),

    # Static menu page with .html: /pro-fpu/istoriya-fpu.html
    re_path(
        r"^(?P<path>[\w-]+(?:/[\w-]+)*)\.html$",
        views.static_page,
        name="static_page",
    ),

    # Static menu page without .html: /pro-fpu or /pro-fpu/istoriya-fpu
    re_path(
        r"^(?P<path>[\w-]+(?:/[\w-]+)*)$",
        views.static_page_no_ext,
        name="static_page_no_ext",
    ),
]
