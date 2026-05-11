from __future__ import annotations

from django.urls import path, re_path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("contacts/", views.contact, name="contact"),

    # Редиректи для старих Joomla index.php URL (301 Permanent)
    # Матчить: index.php / something/index.php / a/b/c/index.php
    re_path(
        r"^(?:[\w-]+/)*index\.php$",
        views.joomla_redirect,
        name="joomla_redirect",
    ),
]
