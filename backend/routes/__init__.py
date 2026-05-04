from flask import Flask

from backend.routes.auth import auth_bp
from backend.routes.geocoding import geocoding_bp
from backend.routes.health import health_bp
from backend.routes.locations import locations_bp
from backend.routes.photos import photos_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(geocoding_bp, url_prefix="/api/geocode")
    app.register_blueprint(locations_bp, url_prefix="/api/locations")
    app.register_blueprint(photos_bp, url_prefix="/api/locations")
