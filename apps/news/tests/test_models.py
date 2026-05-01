from __future__ import annotations

import pytest

from apps.news.factories import ArticleFactory


@pytest.mark.django_db
def test_article_factory_creates_instance():
    article = ArticleFactory()
    assert article.pk is not None
    assert article.title
    assert article.slug
    assert article.is_published is True


@pytest.mark.django_db
def test_article_slug_auto_uniquifies():
    a = ArticleFactory(title="Привіт Світ")
    b = ArticleFactory(title="Привіт Світ")
    assert a.slug != b.slug


@pytest.mark.django_db
def test_article_default_ordering_is_recent_first():
    from django.utils import timezone
    from datetime import timedelta

    older = ArticleFactory(published_at=timezone.now() - timedelta(days=5))
    newer = ArticleFactory(published_at=timezone.now())

    from apps.news.models import Article
    qs = list(Article.objects.all())
    assert qs[0].pk == newer.pk
    assert qs[1].pk == older.pk
