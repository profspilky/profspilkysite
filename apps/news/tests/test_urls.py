"""Tests for Joomla-compatible URL patterns and article/category views."""
from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.news.factories import ArticleFactory, CategoryFactory


@pytest.fixture
def cat(db):
    return CategoryFactory(
        joomla_id=999,
        alias="test-cat",
        path="test-cat",
        is_active=True,
    )


@pytest.fixture
def article(cat, db):
    return ArticleFactory(
        joomla_id=12345,
        slug="test-article",
        category=cat,
        is_published=True,
    )


@pytest.mark.django_db
def test_article_in_cat_returns_200(client: Client, article):
    url = f"/test-cat/12345-test-article.html"
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_article_slug_mismatch_still_200(client: Client, article):
    """Wrong slug: canonical URL in response ensures SEO correctness."""
    url = "/test-cat/12345-wrong-slug.html"
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_unknown_joomla_id_returns_404(client: Client, cat):
    url = "/test-cat/99999-missing-article.html"
    resp = client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_category_list_returns_200(client: Client, cat):
    resp = client.get("/test-cat/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_article_context_has_seo_fields(client: Client, article):
    url = f"/test-cat/12345-test-article.html"
    resp = client.get(url)
    assert "page_meta_title" in resp.context
    assert "page_meta_description" in resp.context
    assert "canonical_url" in resp.context


@pytest.mark.django_db
def test_robots_txt(client: Client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert b"User-agent" in resp.content
    assert b"Disallow: /admin/" in resp.content


@pytest.mark.django_db
def test_sitemap_xml(client: Client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert b"urlset" in resp.content
