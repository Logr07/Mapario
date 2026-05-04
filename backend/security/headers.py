"""HTTP bezpečnostní hlavičky aplikované na každou odpověď."""

from flask import Response, current_app


def apply_security_headers(response: Response) -> Response:
    """Flask ``after_request`` hook aplikující bezpečnostní HTTP hlavičky.

    Hlavičky jsou nastavovány přes :meth:`setdefault`, aby je route handler mohl
    přepsat dle potřeby. HSTS a bezpečnostní hlavičky lze vypnout přes konfiguraci
    pro lokální vývoj.
    """
    if not current_app.config.get("SECURITY_HEADERS_ENABLED", True):
        return response

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    )
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Content-Security-Policy", _content_security_policy())

    if current_app.config.get("HSTS_ENABLED", True):
        max_age = current_app.config.get("HSTS_MAX_AGE", 31536000)
        response.headers.setdefault(
            "Strict-Transport-Security",
            f"max-age={max_age}; includeSubDomains",
        )

    return response


def _content_security_policy() -> str:
    """Sestavuje hodnotu hlavičky Content-Security-Policy ze seznamu direktiv."""
    directives = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://*.google.com https://*.gstatic.com",
        "font-src 'self' data:",
        "connect-src 'self' ws: wss:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    return "; ".join(directives)
