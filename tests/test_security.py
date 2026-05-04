from backend import create_app
from backend.services.auth_service import AuthService


def test_security_headers_are_applied():
    app = create_app(config_overrides={"TESTING": True})
    client = app.test_client()

    response = client.get("/api/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_session_cookie_uses_secure_flags():
    app = create_app(config_overrides={"TESTING": True})
    client = app.test_client()

    response = client.get("/api/auth/csrf")
    set_cookie = response.headers["Set-Cookie"]

    assert set_cookie.startswith("__Host-mapa_session=")
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie
    assert "Path=/" in set_cookie


def test_password_hashes_are_salted_and_verifiable():
    auth_service = AuthService()
    password = "safe-test-password"

    first_hash = auth_service.hash_password(password)
    second_hash = auth_service.hash_password(password)

    assert first_hash != second_hash
    assert password not in first_hash
    assert auth_service.verify_password(first_hash, password)
    assert not auth_service.verify_password(first_hash, "wrong-password")
