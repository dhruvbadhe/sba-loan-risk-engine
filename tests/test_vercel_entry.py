def test_vercel_serves_dashboard_and_existing_api(api):
    from fastapi.testclient import TestClient
    from api.index import app

    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/_stcore/health").status_code == 200
        assert client.get("/health").json()["status"] == "healthy"
        assert "/predict" in client.get("/openapi.json").json()["paths"]
        assert client.post("/predict", json={}).status_code == 401
