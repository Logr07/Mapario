"""Továrna na Flask aplikaci."""

from flask import Flask

from backend.config import Config
from backend.repositories.db import Database
from backend.routes import register_blueprints
from backend.security.csrf import validate_csrf
from backend.security.headers import apply_security_headers


def create_app(config_object: type[Config] = Config, config_overrides: dict | None = None) -> Flask:
    """Vytvoří a nakonfiguruje Flask aplikaci.

    Args:
        config_object: Třída s konfigurací aplikace.
        config_overrides: Volitelný slovník hodnot přepisujících konfiguraci (využití v testech).

    Returns:
        Nakonfigurovaná instance Flask aplikace.
    """
    app = Flask(__name__)
    app.config.from_object(config_object)
    if config_overrides:
        app.config.update(config_overrides)

    app.secret_key = app.config["SECRET_KEY"]
    app.extensions["database"] = Database(app.config["DATABASE_URL"])
    app.before_request(validate_csrf)
    app.after_request(apply_security_headers)

    register_blueprints(app)
    return app
