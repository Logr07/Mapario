from backend.repositories.db import Database


class HealthService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_status(self) -> tuple[dict, int]:
        try:
            database_ok = self.database.ping()
        except Exception as exc:
            return {
                "status": "degraded",
                "database": "unavailable",
                "detail": str(exc),
            }, 503

        if database_ok:
            return {"status": "ok", "database": "ok"}, 200

        return {"status": "degraded", "database": "unexpected-response"}, 503

