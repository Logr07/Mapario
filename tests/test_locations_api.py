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
        pytest.skip("DATABASE_URL is required for locations API integration tests.")
    return Database(database_url)


@pytest.fixture
def app(database):
    return create_app(
        config_overrides={
            "DATABASE_URL": database.database_url,
            "SECRET_KEY": "test-secret",
            "TESTING": True,
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
            cursor.execute("DELETE FROM users WHERE email LIKE %s", ("loc-%@example.test",))


def unique_email() -> str:
    return f"loc-{uuid4().hex}@example.test"


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
        "title": "Opuštěná tovární hala",
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


def test_locations_api_requires_login(client):
    response = client.post("/api/locations", json=location_payload(), headers=csrf_headers(client))

    assert response.status_code == 401


def test_locations_api_creates_lists_and_reads_location(client):
    register(client)

    create_response = client.post("/api/locations", json=location_payload(), headers=csrf_headers(client))
    assert create_response.status_code == 201
    created = create_response.get_json()["location"]

    list_response = client.get("/api/locations")
    detail_response = client.get(f"/api/locations/{created['id']}")

    assert list_response.status_code == 200
    assert [location["id"] for location in list_response.get_json()["locations"]] == [created["id"]]
    assert detail_response.status_code == 200
    assert detail_response.get_json()["location"]["title"] == "Opuštěná tovární hala"
    assert detail_response.get_json()["location"]["is_favorite"] is False
    assert "description" not in detail_response.get_json()["location"]
    assert "cadastral_status" not in detail_response.get_json()["location"]
    assert "notes" not in detail_response.get_json()["location"]


def test_locations_api_validates_payload(client):
    register(client)

    response = client.post(
        "/api/locations",
        json=location_payload(latitude=120),
        headers=csrf_headers(client),
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_locations_api_allows_empty_title(client):
    register(client)

    response = client.post(
        "/api/locations",
        json=location_payload(title="   "),
        headers=csrf_headers(client),
    )

    assert response.status_code == 201
    assert response.get_json()["location"]["title"] == ""


def test_locations_api_updates_and_deletes_location(client):
    register(client)
    created = client.post("/api/locations", json=location_payload(), headers=csrf_headers(client)).get_json()["location"]

    update_response = client.put(
        f"/api/locations/{created['id']}",
        json=location_payload(
            title="Aktualizovaná lokalita",
            latitude=49.195,
            longitude=16.607,
            status="visited",
            rating="5",
            accessibility="freely_accessible",
        ),
        headers=csrf_headers(client),
    )

    assert update_response.status_code == 200
    updated = update_response.get_json()["location"]
    assert updated["title"] == "Aktualizovaná lokalita"
    assert updated["latitude"] == pytest.approx(49.195)
    assert updated["longitude"] == pytest.approx(16.607)
    assert updated["status"] == "visited"
    assert updated["rating"] == "5"
    assert updated["accessibility"] == "freely_accessible"

    delete_response = client.delete(f"/api/locations/{created['id']}", headers=csrf_headers(client))
    assert delete_response.status_code == 204
    assert client.get(f"/api/locations/{created['id']}").status_code == 404


def test_locations_api_hides_other_users_locations(app):
    first_client = app.test_client()
    second_client = app.test_client()

    register(first_client)
    first_location = first_client.post(
        "/api/locations",
        json=location_payload(),
        headers=csrf_headers(first_client),
    ).get_json()["location"]

    register(second_client)
    second_location = second_client.post(
        "/api/locations",
        json=location_payload(title="Lokace druhého uživatele"),
        headers=csrf_headers(second_client),
    ).get_json()["location"]

    first_list = first_client.get("/api/locations").get_json()["locations"]
    second_list = second_client.get("/api/locations").get_json()["locations"]

    assert [location["id"] for location in first_list] == [first_location["id"]]
    assert [location["id"] for location in second_list] == [second_location["id"]]
    assert second_client.get(f"/api/locations/{first_location['id']}").status_code == 404
    assert second_client.delete(
        f"/api/locations/{first_location['id']}",
        headers=csrf_headers(second_client),
    ).status_code == 404


def test_locations_api_toggles_favorite_location(app):
    first_client = app.test_client()
    second_client = app.test_client()

    register(first_client)
    location = first_client.post(
        "/api/locations",
        json=location_payload(),
        headers=csrf_headers(first_client),
    ).get_json()["location"]

    favorite_response = first_client.put(
        f"/api/locations/{location['id']}/favorite",
        json={"is_favorite": True},
        headers=csrf_headers(first_client),
    )

    assert favorite_response.status_code == 200
    assert favorite_response.get_json()["location"]["is_favorite"] is True
    assert first_client.get("/api/locations").get_json()["locations"][0]["is_favorite"] is True

    unfavorite_response = first_client.put(
        f"/api/locations/{location['id']}/favorite",
        json={"is_favorite": False},
        headers=csrf_headers(first_client),
    )

    assert unfavorite_response.status_code == 200
    assert unfavorite_response.get_json()["location"]["is_favorite"] is False

    register(second_client)
    assert second_client.put(
        f"/api/locations/{location['id']}/favorite",
        json={"is_favorite": True},
        headers=csrf_headers(second_client),
    ).status_code == 404


def test_locations_api_validates_favorite_payload(client):
    register(client)
    location = client.post("/api/locations", json=location_payload(), headers=csrf_headers(client)).get_json()["location"]

    response = client.put(
        f"/api/locations/{location['id']}/favorite",
        json={"is_favorite": "yes"},
        headers=csrf_headers(client),
    )

    assert response.status_code == 400
