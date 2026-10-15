import pytest
from pydantic import ValidationError


def test_disallowed_origin_has_no_cors_access_header(api):
    response = api.client.get(
        "/health", headers={"Origin": "https://untrusted.invalid"}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_disallowed_preflight_is_rejected(api):
    response = api.client.options(
        "/predict",
        headers={
            "Origin": "https://untrusted.invalid",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-KEY,Content-Type",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_local_development_origin_is_allowed(api):
    response = api.client.get("/health", headers={"Origin": "http://localhost:8501"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:8501"


def test_origins_are_read_from_comma_separated_environment(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv(
        "CORS_ORIGINS", " https://dashboard.example.com, https://other.example.com, "
    )
    assert Settings().cors_origins == [
        "https://dashboard.example.com",
        "https://other.example.com",
    ]


def test_empty_origins_deny_all_browser_origins(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", " , ")
    assert Settings().cors_origins == []


def test_wildcard_origins_are_rejected(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", "https://dashboard.example.com,*")
    with pytest.raises(ValidationError, match="explicit origins"):
        Settings()
