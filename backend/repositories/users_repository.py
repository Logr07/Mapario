"""Datová vrstva pro správu uživatelských účtů."""

from backend.repositories.db import Database


class UsersRepository:
    """Operace čtení a zápisu nad tabulkou ``users``.

    E-mailové adresy jsou před uložením i porovnáním vždy normalizovány
    (zbavení mezer a převod na malá písmena).
    """
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_user(self, email: str, password_hash: str) -> dict:
        normalized_email = self._normalize_email(email)
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (email, password_hash)
                    VALUES (%s, %s)
                    RETURNING id, email, password_hash
                    """,
                    (normalized_email, password_hash),
                )
                row = cursor.fetchone()

        return self._row_to_user(row)

    def find_by_id(self, user_id: int) -> dict | None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, email, password_hash
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    def find_by_email(self, email: str) -> dict | None:
        normalized_email = self._normalize_email(email)
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, email, password_hash
                    FROM users
                    WHERE email = %s
                    """,
                    (normalized_email,),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    def update_password(self, user_id: int, new_password_hash: str) -> None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (new_password_hash, user_id),
                )

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def _row_to_user(self, row) -> dict:
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
        }
