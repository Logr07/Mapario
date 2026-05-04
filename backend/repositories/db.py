"""Pomocná třída pro práci s databázovým spojením."""

import psycopg


class Database:
    """Tenký obal nad connection stringem pro psycopg.

    Každé volání :meth:`connect` otevře nové spojení, které je určeno k použití
    jako context manager — spojení se po ukončení bloku automaticky potvrdí a zavře.
    """
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, connect_timeout=5)

    def ping(self) -> bool:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
        return row == (1,)
