import os
from uuid import uuid4

import pytest

from backend import create_app
from backend.repositories.db import Database
from backend.routes import geocoding
from tests.csrf_helpers import csrf_headers


@pytest.fixture
def database():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for geocoding API integration tests.")
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
            cursor.execute("DELETE FROM users WHERE email LIKE %s", ("geo-%@example.test",))


def register(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"geo-{uuid4().hex}@example.test",
            "password": "safe-test-password",
            "display_name": "Testovací uživatel",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 201


def test_geocode_requires_login(client):
    response = client.get("/api/geocode?query=Praha")

    assert response.status_code == 401


def test_geocode_validates_query_length(client):
    register(client)

    response = client.get("/api/geocode?query=Pr")

    assert response.status_code == 400


def test_geocode_returns_normalized_results(client, monkeypatch):
    register(client)

    def fake_search(query, **kwargs):
        assert query == "Praha"
        return [
            {
                "id": "N:435514",
                "display_name": "Praha, Hlavní město Praha, Česko",
                "latitude": 50.0874654,
                "longitude": 14.4212535,
                "category": "place",
                "type": "city",
                "source": "photon",
            }
        ]

    monkeypatch.setattr(geocoding._geocoding_service, "search", fake_search)

    response = client.get("/api/geocode?query=Praha")

    assert response.status_code == 200
    assert response.get_json()["results"][0]["display_name"].startswith("Praha")


def test_geocode_suggest_uses_same_search(client, monkeypatch):
    register(client)
    monkeypatch.setattr(geocoding._geocoding_service, "search", lambda query, **kwargs: [])

    response = client.get("/api/geocode/suggest?query=Pra")

    assert response.status_code == 200
    assert response.get_json() == {"results": []}
