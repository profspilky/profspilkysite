"""Tests for search and contact views."""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.news.models import Article


@pytest.mark.django_db
def test_search_get_200(client):
    response = client.get(reverse("core:search"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_search_with_query(client):
    Article.objects.create(
        title="Профспілки захищають права",
        slug="profspilky-zahyst",
        summary="Тест профспілки.",
        is_published=True,
    )
    response = client.get(reverse("core:search") + "?q=профспілки")
    assert response.status_code == 200
    assert "профспілки".encode() in response.content.lower() or b"profspilky" in response.content


@pytest.mark.django_db
def test_search_empty_query(client):
    response = client.get(reverse("core:search") + "?q=")
    assert response.status_code == 200


@pytest.mark.django_db
def test_contact_get_200(client):
    response = client.get(reverse("core:contact"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_contact_post_invalid(client):
    response = client.post(reverse("core:contact"), {
        "name": "",
        "email": "invalid",
        "subject": "",
        "message": "ok",
    })
    assert response.status_code == 200
    assert b"form" in response.content


@pytest.mark.django_db
def test_contact_post_valid(client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    response = client.post(reverse("core:contact"), {
        "name": "Тест Тестовий",
        "email": "test@example.com",
        "subject": "Тестова тема",
        "message": "Це тестове повідомлення для перевірки форми зворотного зв'язку.",
    })
    assert response.status_code == 200
