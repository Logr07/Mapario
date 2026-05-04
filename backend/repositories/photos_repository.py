"""Datová vrstva pro správu fotografii lokácí."""

from backend.repositories.db import Database


class PhotosRepository:
    """CRUD operace nad tabulkou ``location_photos``.

    Vlastnictví se vždy ověřuje přes JOIN na tabulku ``locations``, tudíž
    uživatelé mají přístup pouze k fotografiím svých vlastních lokácí.
    """
    def __init__(self, database: Database) -> None:
        self.database = database

    def location_belongs_to_user(self, user_id: int, location_id: int) -> bool:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM locations
                    WHERE user_id = %s AND id = %s
                    """,
                    (user_id, location_id),
                )
                return cursor.fetchone() == (1,)

    def list_for_location(self, user_id: int, location_id: int) -> list[dict] | None:
        if not self.location_belongs_to_user(user_id, location_id):
            return None

        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.location_id,
                        p.file_path,
                        p.original_filename,
                        p.created_at
                    FROM location_photos p
                    JOIN locations l ON l.id = p.location_id
                    WHERE l.user_id = %s AND p.location_id = %s
                    ORDER BY p.created_at DESC, p.id DESC
                    """,
                    (user_id, location_id),
                )
                rows = cursor.fetchall()

        return [self._row_to_photo(row) for row in rows]

    def get_for_user(self, user_id: int, location_id: int, photo_id: int) -> dict | None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.location_id,
                        p.file_path,
                        p.original_filename,
                        p.created_at
                    FROM location_photos p
                    JOIN locations l ON l.id = p.location_id
                    WHERE l.user_id = %s AND p.location_id = %s AND p.id = %s
                    """,
                    (user_id, location_id, photo_id),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_photo(row)

    def create_for_location(
        self,
        user_id: int,
        location_id: int,
        file_path: str,
        original_filename: str,
    ) -> dict | None:
        """Uloží nový záznam fotografie poté, co byl soubor uložen na disk.

        Vrací ``None``, pokud ověření vlastnictví selhá, v takovém případě
        by volající měl načtený soubor smazat.
        """
        if not self.location_belongs_to_user(user_id, location_id):
            return None

        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO location_photos (location_id, file_path, original_filename)
                    VALUES (%s, %s, %s)
                    RETURNING id, location_id, file_path, original_filename, created_at
                    """,
                    (location_id, file_path, original_filename),
                )
                row = cursor.fetchone()

        return self._row_to_photo(row)

    def delete_for_user(self, user_id: int, location_id: int, photo_id: int) -> dict | None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM location_photos p
                    USING locations l
                    WHERE
                        l.id = p.location_id
                        AND l.user_id = %s
                        AND p.location_id = %s
                        AND p.id = %s
                    RETURNING p.id, p.location_id, p.file_path, p.original_filename, p.created_at
                    """,
                    (user_id, location_id, photo_id),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_photo(row)

    def _row_to_photo(self, row) -> dict:
        return {
            "id": row[0],
            "location_id": row[1],
            "file_path": row[2],
            "original_filename": row[3],
            "created_at": row[4].isoformat(),
            "url": f"/api/locations/{row[1]}/photos/{row[0]}/file",
        }
