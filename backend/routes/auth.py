"""Autentizační endpointy: registrace, přihlášení, odhlášení, info o session, změna hesla."""

from flask import Blueprint, current_app, jsonify, request, session

from backend.repositories.users_repository import UsersRepository
from backend.security.csrf import get_csrf_token, rotate_csrf_token
from backend.services.auth_service import AuthError, AuthService, LoginRateLimiter

auth_bp = Blueprint("auth", __name__)
_auth_service = AuthService()
_login_rate_limiter = LoginRateLimiter()


@auth_bp.get("/me")
def me():
    user = _current_user()
    if user is not None:
        return jsonify({"authenticated": True, "user": user})
    return jsonify({"authenticated": False, "user": None})


@auth_bp.get("/csrf")
def csrf():
    return jsonify({"csrf_token": get_csrf_token()})


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    users_repository = _users_repository()

    try:
        user = _auth_service.register_user(users_repository, payload)
    except AuthError as exc:
        return jsonify({"error": exc.message}), exc.status_code

    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    return jsonify({"authenticated": True, "user": user, "csrf_token": rotate_csrf_token()}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    limiter_key = _login_limiter_key(payload)
    if _login_rate_limiter.is_limited(limiter_key):
        return jsonify({"error": "Příliš mnoho neúspěšných pokusů. Zkus to později."}), 429

    users_repository = _users_repository()
    try:
        user = _auth_service.authenticate_user(users_repository, payload)
    except AuthError as exc:
        if exc.status_code == 401:
            _login_rate_limiter.record_failure(limiter_key)
        return jsonify({"error": exc.message}), exc.status_code

    _login_rate_limiter.reset(limiter_key)
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    return jsonify({"authenticated": True, "user": user, "csrf_token": rotate_csrf_token()})


@auth_bp.post("/change-password")
def change_password():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Nejste přihlášeni."}), 401

    payload = request.get_json(silent=True) or {}
    users_repository = _users_repository()

    try:
        _auth_service.change_password(users_repository, user_id, payload)
    except AuthError as exc:
        return jsonify({"error": exc.message}), exc.status_code

    return jsonify({"success": True}), 200


@auth_bp.post("/logout")
def logout():
    session.clear()
    return "", 204


def _current_user() -> dict | None:
    """Zjistí přihlášeného uživatele a vrátí jeho veřejná data, nebo ``None`` pokud není přihlášen.

    Vymaže session, pokud ``user_id`` uložený v session již v databázi neexistuje
    (např. po smazání účtu).
    """
    user_id = session.get("user_id")
    if user_id is None:
        return None

    user = _users_repository().find_by_id(user_id)
    if user is None:
        session.clear()
        return None

    return _auth_service.public_user(user)


def _users_repository() -> UsersRepository:
    return UsersRepository(current_app.extensions["database"])


def _login_limiter_key(payload: dict) -> str:
    """Sestaví klíč ve formátu ``ip:email`` pro bucketě rate-limit čítačů.

    Respektuje hlavičku ``X-Forwarded-For`` pro nasazení za reverzním proxy.
    """
    email = str(payload.get("email", "")).strip().lower()
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    ip_address = forwarded_for.split(",", 1)[0].strip() or request.remote_addr or "unknown"
    return f"{ip_address}:{email}"
