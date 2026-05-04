import io
import os
from uuid import uuid4

import pytest

from backend import create_app
from backend.repositories.db import Database
from tests.csrf_helpers import csrf_headers


@pytest.fixture
def database():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for photos API integration tests.")
    return Database(database_url)


@pytest.fixture
def app(database, tmp_path):
    return create_app(
        config_overrides={
            "DATABASE_URL": database.database_url,
            "SECRET_KEY": "test-secret",
            "TESTING": True,
            "UPLOAD_FOLDER": str(tmp_path),
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def cleanup_test_users(database):
    yield
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE email LIKE %s", ("photo-%@example.test",))


def unique_email() -> str:
    return f"photo-{uuid4().hex}@example.test"


def register(client, email: str | None = None) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email or unique_email(),
            "password": "safe-test-password",
            "display_name": "Testovací uživatel",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 201
    return response.get_json()["user"]


def location_payload(**overrides) -> dict:
    payload = {
        "title": "Lokace s fotkami",
        "latitude": 50.087,
        "longitude": 14.421,
        "status": "unverified",
        "category": "industrial",
        "subcategory": "manufacturing",
        "rating": "3",
        "accessibility": "unknown",
    }
    payload.update(overrides)
    return payload


def create_location(client) -> dict:
    response = client.post("/api/locations", json=location_payload(), headers=csrf_headers(client))
    assert response.status_code == 201
    return response.get_json()["location"]


def photo_upload(filename: str = "lokace.png") -> dict:
    return {"photo": (io.BytesIO(_tiny_png()), filename)}


def _tiny_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x0f"
        b"\x00\x01\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_photos_api_requires_login(client):
    response = client.get("/api/locations/1/photos")

    assert response.status_code == 401


def test_photos_api_uploads_lists_serves_and_deletes_photo(client):
    register(client)
    location = create_location(client)

    upload_response = client.post(
        f"/api/locations/{location['id']}/photos",
        data=photo_upload(),
        content_type="multipart/form-data",
        headers=csrf_headers(client),
    )

    assert upload_response.status_code == 201
    photo = upload_response.get_json()["photo"]
    assert photo["original_filename"] == "lokace.png"
    assert photo["url"] == f"/api/locations/{location['id']}/photos/{photo['id']}/file"

    list_response = client.get(f"/api/locations/{location['id']}/photos")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.get_json()["photos"]] == [photo["id"]]

    file_response = client.get(photo["url"])
    assert file_response.status_code == 200
    assert file_response.content_type == "image/png"
    assert file_response.data.startswith(b"\x89PNG")

    delete_response = client.delete(
        f"/api/locations/{location['id']}/photos/{photo['id']}",
        headers=csrf_headers(client),
    )
    assert delete_response.status_code == 204
    assert client.get(f"/api/locations/{location['id']}/photos").get_json()["photos"] == []
    assert client.get(photo["url"]).status_code == 404


def test_photos_api_validates_uploaded_file(client):
    register(client)
    location = create_location(client)

    response = client.post(
        f"/api/locations/{location['id']}/photos",
        data={"photo": (io.BytesIO(b"not an image"), "soubor.txt")},
        content_type="multipart/form-data",
        headers=csrf_headers(client),
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_photos_api_rejects_spoofed_image_content(client):
    register(client)
    location = create_location(client)

    response = client.post(
        f"/api/locations/{location['id']}/photos",
        data={"photo": (io.BytesIO(b"not an image"), "soubor.png", "image/png")},
        content_type="multipart/form-data",
        headers=csrf_headers(client),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Soubor musí být platný obrázek."


def test_photos_api_rejects_extension_that_does_not_match_content(client):
    register(client)
    location = create_location(client)

    response = client.post(
        f"/api/locations/{location['id']}/photos",
        data={"photo": (io.BytesIO(b"\xff\xd8\xff\xe0fake-jpeg"), "soubor.png", "image/png")},
        content_type="multipart/form-data",
        headers=csrf_headers(client),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Přípona souboru neodpovídá obsahu obrázku."


def test_photos_api_hides_other_users_photos(app):
    first_client = app.test_client()
    second_client = app.test_client()

    register(first_client)
    location = create_location(first_client)
    photo = first_client.post(
        f"/api/locations/{location['id']}/photos",
        data=photo_upload(),
        content_type="multipart/form-data",
        headers=csrf_headers(first_client),
    ).get_json()["photo"]

    register(second_client)

    assert second_client.get(f"/api/locations/{location['id']}/photos").status_code == 404
    assert second_client.get(photo["url"]).status_code == 404
    assert second_client.delete(
        f"/api/locations/{location['id']}/photos/{photo['id']}",
        headers=csrf_headers(second_client),
    ).status_code == 404
