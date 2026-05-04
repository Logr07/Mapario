"""REST endpointy pro CRUD lokácí a správu oblíbených."""

from flask import Blueprint, current_app, jsonify, request

from backend.domain.enums import (
    CATEGORY_SUBCATEGORIES,
    LocationAccessibility,
    LocationCategory,
    LocationRating,
    LocationStatus,
    LocationSubcategory,
)
from backend.repositories.locations_repository import LocationsRepository
from backend.routes.helpers import get_current_user_id

locations_bp = Blueprint("locations", __name__)

DEFAULT_SUBCATEGORY_BY_CATEGORY = {
    LocationCategory.RESIDENTIAL.value: LocationSubcategory.OTHER_RESIDENTIAL.value,
    LocationCategory.INDUSTRIAL.value: LocationSubcategory.OTHER_INDUSTRIAL.value,
    LocationCategory.PUBLIC.value: LocationSubcategory.OTHER_PUBLIC.value,
    LocationCategory.COMMERCIAL.value: LocationSubcategory.OTHER_COMMERCIAL.value,
    LocationCategory.MILITARY.value: LocationSubcategory.OTHER_MILITARY.value,
    LocationCategory.OTHER.value: LocationSubcategory.OTHER.value,
}


@locations_bp.get("")
def list_locations():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    return jsonify({"locations": _locations_repository().list_for_user(user_id)})


@locations_bp.get("/<int:location_id>")
def get_location(location_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    location = _locations_repository().get_for_user(user_id, location_id)
    if location is None:
        return jsonify({"error": "Lokace nebyla nalezena."}), 404

    return jsonify({"location": location})


@locations_bp.post("")
def create_location():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    try:
        payload = _validated_location_payload()
    except LocationValidationError as exc:
        return jsonify({"error": exc.message}), 400

    location = _locations_repository().create_for_user(user_id, payload)
    return jsonify({"location": location}), 201


@locations_bp.put("/<int:location_id>")
def update_location(location_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    try:
        payload = _validated_location_payload()
    except LocationValidationError as exc:
        return jsonify({"error": exc.message}), 400

    location = _locations_repository().update_for_user(user_id, location_id, payload)
    if location is None:
        return jsonify({"error": "Lokace nebyla nalezena."}), 404

    return jsonify({"location": location})


@locations_bp.delete("/<int:location_id>")
def delete_location(location_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    deleted = _locations_repository().delete_for_user(user_id, location_id)
    if not deleted:
        return jsonify({"error": "Lokace nebyla nalezena."}), 404

    return "", 204


@locations_bp.put("/<int:location_id>/favorite")
def set_location_favorite(location_id: int):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("is_favorite"), bool):
        return jsonify({"error": "Hodnota is_favorite musí být true nebo false."}), 400

    location = _locations_repository().set_favorite_for_user(user_id, location_id, payload["is_favorite"])
    if location is None:
        return jsonify({"error": "Lokace nebyla nalezena."}), 404

    return jsonify({"location": location})


class LocationValidationError(Exception):
    """Vyvolatá funkcí :func:`_validated_location_payload` při selhání validace těla požadavku."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message



def _locations_repository() -> LocationsRepository:
    return LocationsRepository(current_app.extensions["database"])


def _validated_location_payload() -> dict:
    """Parsuje a validuje JSON tělo požadavku pro operace create/update.

    Raises:
        LocationValidationError: Pokud chybí povinné pole, hodnota je mimo rozsah,
            nebo podkategorie nepatjí k vybrané kategorii.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise LocationValidationError("Pošli data lokace ve formátu JSON.")

    title = str(payload.get("title", "")).strip()
    if not title:
        raise LocationValidationError("Popis lokace je povinný.")
    if len(title) > 180:
        raise LocationValidationError("Popis lokace je příliš dlouhý.")

    latitude = _coordinate(payload.get("latitude"), "latitude", -90, 90)
    longitude = _coordinate(payload.get("longitude"), "longitude", -180, 180)

    category = _enum_value(payload.get("category", LocationCategory.OTHER.value), LocationCategory, "category")
    subcategory = _enum_value(
        payload.get("subcategory", _default_subcategory(category)),
        LocationSubcategory,
        "subcategory",
    )
    if subcategory not in CATEGORY_SUBCATEGORIES[category]:
        raise LocationValidationError("Podtyp neodpovídá vybrané kategorii.")

    return {
        "title": title,
        "latitude": latitude,
        "longitude": longitude,
        "status": _enum_value(payload.get("status", LocationStatus.UNSORTED.value), LocationStatus, "status"),
        "category": category,
        "subcategory": subcategory,
        "rating": _enum_value(payload.get("rating", LocationRating.UNRATED.value), LocationRating, "rating"),
        "accessibility": _enum_value(
            payload.get("accessibility", LocationAccessibility.UNKNOWN.value),
            LocationAccessibility,
            "accessibility",
        ),
    }


def _coordinate(value, field_name: str, minimum: float, maximum: float) -> float:
    """Zkonvertuje *value* na float a ověří, zda je v rozsahu [*minimum*, *maximum*].

    Raises:
        LocationValidationError: Při chybě typu nebo překročení rozsahu.
    """
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise LocationValidationError(f"Hodnota {field_name} musí být číslo.") from exc

    if not minimum <= coordinate <= maximum:
        raise LocationValidationError(f"Hodnota {field_name} je mimo platný rozsah.")

    return coordinate


def _enum_value(value, enum_class, field_name: str) -> str:
    normalized_value = str(value).strip()
    allowed_values = {item.value for item in enum_class}
    if normalized_value not in allowed_values:
        raise LocationValidationError(f"Hodnota {field_name} není podporovaná.")
    return normalized_value


def _default_subcategory(category: str) -> str:
    return DEFAULT_SUBCATEGORY_BY_CATEGORY[category]
