"""Ochrana proti CSRF pro mutující API endpointy založená na session tokenu."""

import hmac
import secrets

from flask import jsonify, request, session

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_SESSION_KEY = "csrf_token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_csrf_token() -> str:
    """Vrátí aktuální CSRF token ze session; pokud neexistuje, vygeneruje nový."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = rotate_csrf_token()
    return str(token)


def rotate_csrf_token() -> str:
    """Vygeneruje nový CSRF token, uloží ho do session a vrátí ho."""
    token = secrets.token_urlsafe(32)
    session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf():
    """Flask ``before_request`` hook odmítající mutující požadavky s neplatným CSRF tokenem.

    Bezpečné metody (GET, HEAD, OPTIONS, TRACE) a endpoint pro získání tokenu jsou vyjmuty.
    Porovnání tokenu používá :func:`hmac.compare_digest`, aby se zabránilo timing útokům.
    """
    if request.method in SAFE_METHODS or not request.path.startswith("/api/"):
        return None

    expected_token = session.get(CSRF_SESSION_KEY)
    provided_token = request.headers.get(CSRF_HEADER_NAME, "")
    if (
        not expected_token
        or not provided_token
        or not hmac.compare_digest(str(expected_token), str(provided_token))
    ):
        return jsonify({"error": "Neplatný nebo chybějící CSRF token."}), 403

    return None
