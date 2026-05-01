from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_returns_200(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_home_uses_correct_template(client):
    response = client.get(reverse("core:home"))
    template_names = [t.name for t in response.templates if t.name]
    assert "core/home.html" in template_names
    assert "base.html" in template_names


@pytest.mark.django_db
def test_home_provides_context(client):
    response = client.get(reverse("core:home"))
    assert "articles" in response.context
    assert "priorities" in response.context
    assert "team_members" in response.context
    assert len(response.context["priorities"]) >= 4
    assert len(response.context["articles"]) >= 4
    assert len(response.context["team_members"]) >= 4


@pytest.mark.django_db
def test_home_renders_critical_sections(client):
    response = client.get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert 'class="hero"' in body
    assert "news-feed" in body
    assert 'class="priorities-panel"' in body
    assert "team" in body
