from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert "version" in json_data
    assert json_data["api_v1"] == "/api/v1"


def test_health_live_endpoint(client: TestClient):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "alive"
    assert "version" in json_data["data"]
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers


def test_health_ready_endpoint(client: TestClient):
    response = client.get("/api/v1/health/ready")
    assert response.status_code in [200, 503]
    json_data = response.json()
    assert "data" in json_data
    assert "checks" in json_data["data"]
