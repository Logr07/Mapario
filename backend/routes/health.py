from flask import Blueprint, current_app, jsonify

from backend.services.health_service import HealthService

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    service = HealthService(current_app.extensions["database"])
    payload, status_code = service.get_status()
    return jsonify(payload), status_code

