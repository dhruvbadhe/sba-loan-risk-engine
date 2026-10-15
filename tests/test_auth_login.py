import socket
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_KEY", "")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-jwt-secret-for-login-tests")

    def reject_network(*args, **kwargs):
        raise AssertionError("Network access is forbidden in login tests")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr("supabase.create_client", Mock(return_value=None))

    from app.core.config import settings

    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_KEY", "")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-only-jwt-secret-for-login-tests")

    from app.api import routes_auth

    monkeypatch.setattr(routes_auth, "supabase_client", None)
    app = FastAPI()
    app.include_router(routes_auth.router)

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "username,password",
    [("admin", "admin"), ("test-user", "test-only-password")],
    ids=["former-admin-backdoor", "ordinary-credentials"],
)
def test_login_without_database_returns_503(client, username, password):
    response = client.post("/login", data={"username": username, "password": password})

    assert response.status_code == 503
    assert response.json() == {"detail": "Database connection is not configured."}


def test_login_with_database_verifies_password_and_issues_token(client, monkeypatch):
    from app.api import routes_auth
    from app.core.security import decode_access_token, get_password_hash

    database = Mock()
    database.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"password_hash": get_password_hash("test-only-password")}
    ]
    monkeypatch.setattr(routes_auth, "supabase_client", database)

    response = client.post(
        "/login", data={"username": "test-user", "password": "test-only-password"}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert decode_access_token(response.json()["access_token"])["sub"] == "test-user"
    database.table.assert_called_once_with("users")
    database.table.return_value.select.return_value.eq.assert_called_once_with(
        "username", "test-user"
    )
