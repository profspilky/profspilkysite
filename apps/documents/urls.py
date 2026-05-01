"""Documents URL patterns."""
from __future__ import annotations

from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("documents/", views.document_index, name="document_index"),
    path("documents/<slug:slug>/", views.category_detail, name="category_detail"),
]
