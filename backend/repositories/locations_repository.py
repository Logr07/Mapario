"""Datová vrstva pro správu lokácí a jejich bodů zájmu."""

from backend.repositories.db import Database


class LocationsRepository:
    """CRUD operace nad tabulkami ``locations`` a ``points_of_interest``.

    Všechny dotazy jsou omezené na vlastníka, tudíž uživatel nemůže
    číst ani upravovat lokáce patřící jinému účtu.
    """
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_for_user(self, user_id: int) -> list[dict]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self._base_select() + " WHERE l.user_id = %s ORDER BY l.updated_at DESC", (user_id,))
                rows = cursor.fetchall()

        return [self._row_to_location(row) for row in rows]

    def get_for_user(self, user_id: int, location_id: int) -> dict | None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self._base_select() + " WHERE l.user_id = %s AND l.id = %s",
                    (user_id, location_id),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_location(row)

    def create_for_user(self, user_id: int, payload: dict) -> dict:
        """Vloží novou lokáci spolu se záznamem POI metadat.

        Geometrie je uložena jako PostGIS bod v SRID 4326.
        Vyvoívá :class:`RuntimeError`, pokud se nově vytvořený záznam nepodaří zpětně načíst
        (za normálních okolností by k tomu nemělo dojít).
        """
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO locations (user_id, title, geom)
                    VALUES (
                        %s,
                        %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    )
                    RETURNING id
                    """,
                    (
                        user_id,
                        payload["title"].strip(),
                        payload["longitude"],
                        payload["latitude"],
                    ),
                )
                location_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO points_of_interest (
                        location_id,
                        status,
                        category,
                        subcategory,
                        rating,
                        accessibility
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        location_id,
                        payload.get("status", "unsorted"),
                        payload.get("category", "other"),
                        payload.get("subcategory", "other"),
                        payload.get("rating", "unrated"),
                        payload.get("accessibility", "unknown"),
                    ),
                )

        location = self.get_for_user(user_id, location_id)
        if location is None:
            raise RuntimeError("Created location could not be loaded.")
        return location

    def update_for_user(self, user_id: int, location_id: int, payload: dict) -> dict | None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE locations
                    SET
                        title = %s,
                        geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        updated_at = now()
                    WHERE user_id = %s AND id = %s
                    RETURNING id
                    """,
                    (
                        payload["title"].strip(),
                        payload["longitude"],
                        payload["latitude"],
                        user_id,
                        location_id,
                    ),
                )
                updated_row = cursor.fetchone()
                if updated_row is None:
                    return None

                cursor.execute(
                    """
                    UPDATE points_of_interest
                    SET
                        status = %s,
                        category = %s,
                        subcategory = %s,
                        rating = %s,
                        accessibility = %s
                    WHERE location_id = %s
                    """,
                    (
                        payload.get("status", "unsorted"),
                        payload.get("category", "other"),
                        payload.get("subcategory", "other"),
                        payload.get("rating", "unrated"),
                        payload.get("accessibility", "unknown"),
                        location_id,
                    ),
                )

        return self.get_for_user(user_id, location_id)

    def delete_for_user(self, user_id: int, location_id: int) -> bool:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM locations
                    WHERE user_id = %s AND id = %s
                    """,
                    (user_id, location_id),
                )
                return cursor.rowcount == 1

    def set_favorite_for_user(self, user_id: int, location_id: int, is_favorite: bool) -> dict | None:
        """Nastaví nebo zruší příznak oblíbené lokáce.

        Používá ``INSERT … ON CONFLICT DO NOTHING``, aby bylo přidání idempotentí.
        Vrací aktualizovaný slovník lokáce, nebo ``None`` pokud lokáce neexistuje
        nebo nepatjí přihlášenému uživateli.
        """
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM locations
                    WHERE user_id = %s AND id = %s
                    """,
                    (user_id, location_id),
                )
                if cursor.fetchone() is None:
                    return None

                if is_favorite:
                    cursor.execute(
                        """
                        INSERT INTO favorite_locations (user_id, location_id)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id, location_id) DO NOTHING
                        """,
                        (user_id, location_id),
                    )
                else:
                    cursor.execute(
                        """
                        DELETE FROM favorite_locations
                        WHERE user_id = %s AND location_id = %s
                        """,
                        (user_id, location_id),
                    )

        return self.get_for_user(user_id, location_id)

    def _base_select(self) -> str:
        """Vrátí společný SELECT fragment používaný všemi čtecími dotazy.

        Joinuje ``points_of_interest`` (vždy přítomné) a ``favorite_locations``
        (volitelně) tak, aby byl kompletní záznam lokáce načten v jednom dotazu.
        """
        return """
            SELECT
                l.id,
                l.user_id,
                l.title,
                ST_Y(l.geom) AS latitude,
                ST_X(l.geom) AS longitude,
                p.status,
                p.category,
                p.subcategory,
                p.rating,
                p.accessibility,
                f.user_id IS NOT NULL AS is_favorite,
                l.created_at,
                l.updated_at
            FROM locations l
            JOIN points_of_interest p ON p.location_id = l.id
            LEFT JOIN favorite_locations f ON f.location_id = l.id AND f.user_id = l.user_id
        """

    def _row_to_location(self, row) -> dict:
        return {
            "id": row[0],
            "user_id": row[1],
            "title": row[2],
            "latitude": float(row[3]),
            "longitude": float(row[4]),
            "status": row[5],
            "category": row[6],
            "subcategory": row[7],
            "rating": row[8],
            "accessibility": row[9],
            "is_favorite": row[10],
            "created_at": row[11].isoformat(),
            "updated_at": row[12].isoformat(),
        }
