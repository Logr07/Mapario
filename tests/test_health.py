from backend import create_app


class HealthyDatabase:
    def ping(self) -> bool:
        return True


def test_health_endpoint_reports_ok():
    app = create_app(config_overrides={"TESTING": True})
    app.extensions["database"] = HealthyDatabase()

    response = app.test_client().get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"database": "ok", "status": "ok"}

