from __future__ import annotations

from django.urls import path, re_path
from django.views.generic import RedirectView

from . import views
from apps.news import views as news_views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("contacts/", views.contact, name="contact"),
    path("novini/", news_views.all_news, name="all_news"),
    re_path(r"^sajty-chlenskykh-orhanizatsii/?$", views.member_sites_page, name="member_sites"),
    path("chlenski-orhanizatsii/<slug:slug>/", views.mem_org_detail, name="mem_org_detail"),
    re_path(r"^spo-ob-?iednan-profspilok/?$", views.spo_page, name="spo"),

    # Редиректи для старих Joomla index.php URL (301 Permanent)
    # Матчить: index.php / something/index.php / a/b/c/index.php
    re_path(
        r"^(?:[\w-]+/)*index\.php$",
        views.joomla_redirect,
        name="joomla_redirect",
    ),
]
