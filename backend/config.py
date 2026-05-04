"""Konfigurace aplikace načîtaná z proměnných prostředí."""

import os


def _env_bool(name: str, default: bool = False) -> bool:
    """Načte proměnnou prostředí jako boolean.

    Jako *True* rozpoznává hodnoty ``1``, ``true``, ``yes`` a ``on`` (case-insensitive).
    Vrací *default*, pokud proměnná není nastavená.
    """
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """Načte proměnnou prostředí jako float; při chybě parsování vrátí *default*."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


class Config:
    """Výchozí konfigurace připravená pro produkční provoz.

    Každou hodnotu lze přepsat odpovídající proměnnou prostředí.
    Citlivé položky (``SECRET_KEY``, ``DATABASE_URL``) je **nutné** před nasazením změnit.
    """
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "development-secret-change-me")
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://interest_map:change-me@localhost:5432/interest_map",
    )
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/app/uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))
    SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "__Host-mapa_session")
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)
    SECURITY_HEADERS_ENABLED = _env_bool("SECURITY_HEADERS_ENABLED", True)
    HSTS_ENABLED = _env_bool("HSTS_ENABLED", True)
    HSTS_MAX_AGE = int(os.environ.get("HSTS_MAX_AGE", str(365 * 24 * 60 * 60)))
    JSON_AS_ASCII = False
    PHOTON_BASE_URL = os.environ.get("PHOTON_BASE_URL", "https://photon.komoot.io")
    PHOTON_USER_AGENT = os.environ.get(
        "PHOTON_USER_AGENT",
        "mapa-bakalarka/0.1 (https://bakalarka.infinitya.eu)",
    )
    PHOTON_TIMEOUT_SECONDS = _env_float("PHOTON_TIMEOUT_SECONDS", 8.0)
