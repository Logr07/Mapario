from flask import Blueprint, current_app, jsonify, request

from backend.routes.helpers import get_current_user_id
from backend.services.geocoding_service import GeocodingProviderError, GeocodingService

geocoding_bp = Blueprint("geocoding", __name__)
_geocoding_service = GeocodingService()


@geocoding_bp.get("")
def geocode():
    if get_current_user_id() is None:
        return jsonify({"error": "Přihlášení je vyžadováno."}), 401

    query = str(request.args.get("query") or request.args.get("q") or "").strip()
    if len(query) < 3:
        return jsonify({"error": "Zadej alespoň 3 znaky adresy."}), 400

    try:
        results = _geocoding_service.search(
            query,
            base_url=current_app.config["PHOTON_BASE_URL"],
            user_agent=current_app.config["PHOTON_USER_AGENT"],
            timeout_seconds=current_app.config["PHOTON_TIMEOUT_SECONDS"],
        )
    except GeocodingProviderError as exc:
        return jsonify({"error": exc.message}), 502

    return jsonify({"results": results})


@geocoding_bp.get("/suggest")
def suggest_addresses():
    return geocode()
