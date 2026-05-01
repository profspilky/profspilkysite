"""News URL patterns — exact Joomla SEF URL compatibility.

Joomla URL structures preserved:
  /<cat_path>/<joomla_id>-<alias>.html   → article in category
  /<joomla_id>-<alias>.html              → article at root (no category path)
  /<cat_path>/                           → category listing
"""
from __future__ import annotations

from django.urls import re_path

from . import views

app_name = "news"

urlpatterns = [
    # Article inside a category path (one or more path segments)
    # e.g. /materialy/29093-vidbuvsia-xiii-forum.html
    # e.g. /pro-fpu/istoriya/123-some-article.html
    re_path(
        r"^(?P<cat_path>[\w-]+(?:/[\w-]+)*)/(?P<joomla_id>\d+)-(?P<slug>[\w-]+)\.html$",
        views.article_in_cat,
        name="article_in_cat",
    ),
    # Category listing page
    # e.g. /materialy/
    re_path(
        r"^(?P<cat_path>[\w-]+(?:/[\w-]+)*)/$",
        views.category_list,
        name="category_list",
    ),
]
