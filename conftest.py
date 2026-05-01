"""Top-level pytest configuration."""
from __future__ import annotations

import pytest


@pytest.fixture
def client_uk(client):
    client.cookies["django_language"] = "uk"
    return client


@pytest.fixture
def client_en(client):
    client.cookies["django_language"] = "en"
    return client
