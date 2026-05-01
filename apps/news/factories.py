from __future__ import annotations

import factory
from django.utils import timezone

from .models import Article, Category


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    joomla_id = factory.Sequence(lambda n: 1000 + n)
    alias = factory.Sequence(lambda n: f"category-{n}")
    title = factory.Sequence(lambda n: f"Категорія {n}")
    path = factory.Sequence(lambda n: f"category-{n}")
    is_active = True


class ArticleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Article

    joomla_id = factory.Sequence(lambda n: 10000 + n)
    title = factory.Sequence(lambda n: f"Стаття №{n}")
    slug = factory.Sequence(lambda n: f"stattia-{n}")
    summary = factory.Faker("sentence", nb_words=10)
    body = factory.Faker("paragraph", nb_sentences=4)
    published_at = factory.LazyFunction(timezone.now)
    is_published = True
    category = None
