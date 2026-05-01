from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_default_language_is_uk(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response["Content-Language"].lower().startswith("uk")


@pytest.mark.django_db
def test_english_prefix_resolves(client):
    response = client.get("/en/")
    assert response.status_code == 200
    assert response["Content-Language"].lower().startswith("en")


@pytest.mark.django_db
def test_set_language_endpoint_exists(client):
    response = client.post("/i18n/setlang/", {"language": "en", "next": "/"})
    assert response.status_code in (302, 200)
