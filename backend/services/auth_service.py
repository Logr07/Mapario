"""Business logika autentizace: registrace, přihlášení, správa hesel."""

import re
import time

from werkzeug.security import check_password_hash, generate_password_hash

from backend.repositories.users_repository import UsersRepository


class AuthError(Exception):
    """Vyvolatá třídou :class:`AuthService` při validaci nebo selhání autentizace.

    Nese HTTP *status_code*, aby ho route handler mohl použít přímo.
    """
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LoginRateLimiter:
    """In-process rate limér s klouzajícím oknem pro failed pokusy o přihlášení.

    Sleduje selhání pro klíč ``(ip, email)`` a blokuje další pokusy, jakmile
    počet *max_attempts* selhání přesahuje *window_seconds*.
    Stav se udržuje pouze v paměti — restartováním workeru se resetuje.
    """
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}

    def is_limited(self, key: str) -> bool:
        attempts = self._fresh_attempts(key)
        return len(attempts) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        attempts = self._fresh_attempts(key)
        attempts.append(time.monotonic())
        self._attempts[key] = attempts

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def _fresh_attempts(self, key: str) -> list[float]:
        """Vrátí čerstvá časová razítka selhání; odstraňuje záznamy mimo okno."""
        now = time.monotonic()
        attempts = [
            attempt_time
            for attempt_time in self._attempts.get(key, [])
            if now - attempt_time <= self.window_seconds
        ]
        self._attempts[key] = attempts
        return attempts


class AuthService:
    """Bezstavová služba pro registraci, autentizaci a změnu hesla."""

    EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    MIN_PASSWORD_LENGTH = 8

    def hash_password(self, password: str) -> str:
        return generate_password_hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)

    def register_user(self, users_repository: UsersRepository, payload: dict) -> dict:
        email = self._normalized_email(payload.get("email", ""))
        password = str(payload.get("password", ""))

        self._validate_registration(email, password)
        if users_repository.find_by_email(email) is not None:
            raise AuthError("Účet s tímto e-mailem už existuje.", 409)

        user = users_repository.create_user(
            email=email,
            password_hash=self.hash_password(password),
        )
        return self.public_user(user)

    def authenticate_user(self, users_repository: UsersRepository, payload: dict) -> dict:
        email = self._normalized_email(payload.get("email", ""))
        password = str(payload.get("password", ""))
        if not email or not password:
            raise AuthError("Vyplň e-mail i heslo.", 400)

        user = users_repository.find_by_email(email)
        if user is None or not self.verify_password(user["password_hash"], password):
            raise AuthError("Neplatný e-mail nebo heslo.", 401)

        return self.public_user(user)

    def change_password(self, users_repository: UsersRepository, user_id: int, payload: dict) -> None:
        old_password = str(payload.get("old_password", ""))
        new_password = str(payload.get("new_password", ""))

        if not old_password or not new_password:
            raise AuthError("Vyplň obě hesla.", 400)

        user = users_repository.find_by_id(user_id)
        if user is None or not self.verify_password(user["password_hash"], old_password):
            raise AuthError("Původní heslo není správné.", 400)

        if len(new_password) < self.MIN_PASSWORD_LENGTH:
            raise AuthError("Nové heslo musí mít alespoň 8 znaků.", 400)

        users_repository.update_password(user_id, self.hash_password(new_password))

    def public_user(self, user: dict) -> dict:
        return {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["email"].split("@")[0],
        }

    def _validate_registration(self, email: str, password: str) -> None:
        if not self.EMAIL_PATTERN.match(email):
            raise AuthError("Zadej platný e-mail.", 400)
        if len(password) < self.MIN_PASSWORD_LENGTH:
            raise AuthError("Heslo musí mít alespoň 8 znaků.", 400)

    def _normalized_email(self, email: object) -> str:
        return str(email).strip().lower()
