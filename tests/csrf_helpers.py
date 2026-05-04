def csrf_headers(client) -> dict:
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.get_json()["csrf_token"]}
