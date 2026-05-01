"""Gallery URL patterns."""
from __future__ import annotations

from django.urls import path

from . import views

app_name = "gallery"

urlpatterns = [
    path("gallery/", views.album_list, name="album_list"),
    path("gallery/<slug:slug>/", views.album_detail, name="album_detail"),
]
