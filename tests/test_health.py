def test_health_returns_standard_shape(client):
    response = client.get("/api/v1/health")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert "database" in body["data"]


def test_unknown_route_returns_standard_error(client):
    response = client.get("/api/v1/does-not-exist")
    body = response.json()

    assert response.status_code == 404
    assert body["success"] is False
    assert body["errors"] == []


def test_security_headers_are_present(client):
    response = client.get("/api/v1/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"