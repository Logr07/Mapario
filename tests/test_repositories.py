import os
from uuid import uuid4

import pytest

from backend.repositories.db import Database
from backend.repositories.locations_repository import LocationsRepository
from backend.repositories.users_repository import UsersRepository
from backend.services.auth_service import AuthService


@pytest.fixture
def database():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for repository integration tests.")
    return Database(database_url)


@pytest.fixture
def users_repository(database):
    return UsersRepository(database)


@pytest.fixture
def locations_repository(database):
    return LocationsRepository(database)


@pytest.fixture(autouse=True)
def cleanup_test_users(database):
    yield
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE email LIKE %s", ("test-%@example.test",))


def unique_email() -> str:
    return f"test-{uuid4().hex}@example.test"


def create_test_user(users_repository, email: str | None = None) -> dict:
    auth_service = AuthService()
    return users_repository.create_user(
        email=email or unique_email(),
        password_hash=auth_service.hash_password("safe-test-password"),
    )


def location_payload(**overrides) -> dict:
    payload = {
        "title": "Opuštěný objekt u řeky",
        "latitude": 50.087,
        "longitude": 14.421,
        "status": "unverified",
        "category": "residential",
        "subcategory": "other_residential",
        "rating": "3",
        "accessibility": "unknown",
    }
    payload.update(overrides)
    return payload


def test_users_repository_creates_and_finds_user(users_repository):
    user = create_test_user(users_repository, email=f"  {unique_email().upper()}  ")

    found_by_email = users_repository.find_by_email(user["email"].upper())
    found_by_id = users_repository.find_by_id(user["id"])

    assert found_by_email == user
    assert found_by_id == user
    assert user["email"] == user["email"].lower()


def test_locations_repository_creates_location_with_postgis_point(
    users_repository,
    locations_repository,
):
    user = create_test_user(users_repository)

    location = locations_repository.create_for_user(user["id"], location_payload())

    assert location["title"] == "Opuštěný objekt u řeky"
    assert location["user_id"] == user["id"]
    assert location["status"] == "unverified"
    assert location["category"] == "residential"
    assert location["subcategory"] == "other_residential"
    assert location["rating"] == "3"
    assert location["accessibility"] == "unknown"
    assert location["is_favorite"] is False
    assert location["latitude"] == pytest.approx(50.087)
    assert location["longitude"] == pytest.approx(14.421)


def test_locations_repository_keeps_users_data_isolated(
    users_repository,
    locations_repository,
):
    owner = create_test_user(users_repository)
    other_user = create_test_user(users_repository)
    owner_location = locations_repository.create_for_user(owner["id"], location_payload(title="Vlastní lokace"))
    locations_repository.create_for_user(other_user["id"], location_payload(title="Cizí lokace"))

    owner_locations = locations_repository.list_for_user(owner["id"])

    assert [location["id"] for location in owner_locations] == [owner_location["id"]]
    assert locations_repository.get_for_user(other_user["id"], owner_location["id"]) is None


def test_locations_repository_updates_and_deletes_owned_location(
    users_repository,
    locations_repository,
):
    user = create_test_user(users_repository)
    location = locations_repository.create_for_user(user["id"], location_payload())

    updated = locations_repository.update_for_user(
        user["id"],
        location["id"],
        location_payload(
            title="Aktualizovaná lokace",
            latitude=49.195,
            longitude=16.607,
            status="visited",
            category="industrial",
            subcategory="manufacturing",
            rating="5",
            accessibility="freely_accessible",
        ),
    )

    assert updated is not None
    assert updated["title"] == "Aktualizovaná lokace"
    assert updated["latitude"] == pytest.approx(49.195)
    assert updated["longitude"] == pytest.approx(16.607)
    assert updated["status"] == "visited"
    assert updated["category"] == "industrial"
    assert updated["subcategory"] == "manufacturing"
    assert updated["rating"] == "5"
    assert updated["accessibility"] == "freely_accessible"

    assert locations_repository.delete_for_user(user["id"], location["id"]) is True
    assert locations_repository.get_for_user(user["id"], location["id"]) is None


def test_locations_repository_marks_owned_location_as_favorite(
    users_repository,
    locations_repository,
):
    owner = create_test_user(users_repository)
    other_user = create_test_user(users_repository)
    location = locations_repository.create_for_user(owner["id"], location_payload())

    favorited = locations_repository.set_favorite_for_user(owner["id"], location["id"], True)

    assert favorited is not None
    assert favorited["is_favorite"] is True
    assert locations_repository.list_for_user(owner["id"])[0]["is_favorite"] is True
    assert locations_repository.set_favorite_for_user(other_user["id"], location["id"], True) is None

    unfavorited = locations_repository.set_favorite_for_user(owner["id"], location["id"], False)

    assert unfavorited is not None
    assert unfavorited["is_favorite"] is False
