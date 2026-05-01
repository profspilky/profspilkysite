"""Gallery views tests."""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.gallery.models import GalleryAlbum, GalleryPhoto


@pytest.fixture
def album(db):
    return GalleryAlbum.objects.create(
        title="Тестовий альбом",
        slug="test-album",
        is_published=True,
    )


@pytest.fixture
def photo(album):
    return GalleryPhoto.objects.create(
        album=album,
        title="Тестове фото",
        image_local="stories/test.jpg",
        order=0,
        is_published=True,
    )


@pytest.mark.django_db
def test_album_list_200(client, album):
    url = reverse("gallery:album_list")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_album_list_shows_published(client, album):
    response = client.get(reverse("gallery:album_list"))
    assert album.title.encode() in response.content


@pytest.mark.django_db
def test_album_list_hides_unpublished(client):
    GalleryAlbum.objects.create(
        title="Прихований альбом",
        slug="hidden-album",
        is_published=False,
    )
    response = client.get(reverse("gallery:album_list"))
    assert b"hidden-album" not in response.content


@pytest.mark.django_db
def test_album_detail_200(client, album, photo):
    url = reverse("gallery:album_detail", kwargs={"slug": album.slug})
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_album_detail_404_unpublished(client):
    a = GalleryAlbum.objects.create(
        title="Hidden", slug="hidden-2", is_published=False
    )
    url = reverse("gallery:album_detail", kwargs={"slug": a.slug})
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_album_detail_contains_photo(client, album, photo):
    url = reverse("gallery:album_detail", kwargs={"slug": album.slug})
    response = client.get(url)
    assert photo.title.encode() in response.content or b"photo-grid" in response.content
