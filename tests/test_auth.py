import os
from uuid import uuid4

import pytest

from backend import create_app
from backend.repositories.db import Database
from backend.repositories.locations_repository import LocationsRepository
from backend.services.auth_service import AuthService
from tests.csrf_helpers import csrf_headers


@pytest.fixture
def database():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for auth integration tests.")
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
            cursor.execute("DELETE FROM users WHERE email LIKE %s", ("auth-%@example.test",))


def unique_email() -> str:
    return f"auth-{uuid4().hex}@example.test"


def register_payload(**overrides) -> dict:
    payload = {
        "email": unique_email(),
        "password": "safe-test-password",
        "display_name": "Testovací uživatel",
    }
    payload.update(overrides)
    return payload


def test_register_logs_user_in(client):
    response = client.post("/api/auth/register", json=register_payload(), headers=csrf_headers(client))

    assert response.status_code == 201
    body = response.get_json()
    assert body["authenticated"] is True
    assert body["user"]["email"].startswith("auth-")
    assert "password_hash" not in body["user"]
    assert body["csrf_token"]

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.get_json()["authenticated"] is True


def test_register_rejects_duplicate_email(client):
    payload = register_payload()
    first_response = client.post("/api/auth/register", json=payload, headers=csrf_headers(client))
    client.post("/api/auth/logout", headers=csrf_headers(client))

    duplicate_response = client.post("/api/auth/register", json=payload, headers=csrf_headers(client))

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_login_and_logout_flow(client):
    payload = register_payload()
    register_response = client.post("/api/auth/register", json=payload, headers=csrf_headers(client))
    assert register_response.status_code == 201
    client.post("/api/auth/logout", headers=csrf_headers(client))

    logged_out_me = client.get("/api/auth/me")
    assert logged_out_me.get_json() == {"authenticated": False, "user": None}

    login_response = client.post(
        "/api/auth/login",
        json={"email": payload["email"].upper(), "password": payload["password"]},
        headers=csrf_headers(client),
    )
    assert login_response.status_code == 200
    assert login_response.get_json()["authenticated"] is True
    assert login_response.get_json()["csrf_token"]

    logout_response = client.post("/api/auth/logout", headers=csrf_headers(client))
    assert logout_response.status_code == 204
    assert client.get("/api/auth/me").get_json() == {"authenticated": False, "user": None}


def test_login_rejects_bad_password(client):
    payload = register_payload()
    client.post("/api/auth/register", json=payload, headers=csrf_headers(client))
    client.post("/api/auth/logout", headers=csrf_headers(client))

    response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": "wrong-password"},
        headers=csrf_headers(client),
    )

    assert response.status_code == 401


def test_register_stores_salted_password_hash(database, client):
    payload = register_payload(password="safe-test-password")

    response = client.post("/api/auth/register", json=payload, headers=csrf_headers(client))

    assert response.status_code == 201
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM users WHERE email = %s", (payload["email"],))
            password_hash = cursor.fetchone()[0]

    assert password_hash != payload["password"]
    assert payload["password"] not in password_hash
    assert len(password_hash.split("$")) >= 3
    assert AuthService().verify_password(password_hash, payload["password"])


def test_login_does_not_accept_sql_injection_email(client):
    payload = register_payload()
    client.post("/api/auth/register", json=payload, headers=csrf_headers(client))
    client.post("/api/auth/logout", headers=csrf_headers(client))

    response = client.post(
        "/api/auth/login",
        json={"email": "' OR '1'='1' --", "password": payload["password"]},
        headers=csrf_headers(client),
    )

    assert response.status_code == 401


def test_locations_require_login_and_return_only_session_user_data(app, client):
    first_payload = register_payload()
    second_payload = register_payload()

    first_response = client.post("/api/auth/register", json=first_payload, headers=csrf_headers(client))
    first_user = first_response.get_json()["user"]
    locations_repository = LocationsRepository(app.extensions["database"])
    first_location = locations_repository.create_for_user(
        first_user["id"],
        {
            "title": "Soukromá lokace",
            "latitude": 50.087,
            "longitude": 14.421,
            "status": "unsorted",
            "category": "other",
            "subcategory": "other",
            "rating": "unrated",
            "accessibility": "unknown",
        },
    )
    client.post("/api/auth/logout", headers=csrf_headers(client))

    unauthorized_response = client.get("/api/locations")
    assert unauthorized_response.status_code == 401

    second_response = client.post("/api/auth/register", json=second_payload, headers=csrf_headers(client))
    second_user = second_response.get_json()["user"]
    locations_repository.create_for_user(
        second_user["id"],
        {
            "title": "Druhá soukromá lokace",
            "latitude": 49.195,
            "longitude": 16.607,
            "status": "unsorted",
            "category": "other",
            "subcategory": "other",
            "rating": "unrated",
            "accessibility": "unknown",
        },
    )

    locations_response = client.get("/api/locations")
    locations = locations_response.get_json()["locations"]

    assert locations_response.status_code == 200
    assert [location["title"] for location in locations] == ["Druhá soukromá lokace"]
    assert all(location["id"] != first_location["id"] for location in locations)


def test_csrf_protects_mutating_requests(client):
    missing_token_response = client.post("/api/auth/register", json=register_payload())
    assert missing_token_response.status_code == 403

    invalid_token_response = client.post(
        "/api/auth/register",
        json=register_payload(),
        headers={"X-CSRF-Token": "not-a-valid-token"},
    )
    assert invalid_token_response.status_code == 403

    token_response = client.get("/api/auth/csrf")
    assert token_response.status_code == 200
    assert token_response.get_json()["csrf_token"]
