import socket

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Import settings from an empty directory so the local .env is never read.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_KEY", "test-only-api-key")

    def reject_network(*args, **kwargs):
        raise AssertionError("Network access is forbidden in auth tests")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)

    from app.core import dependencies

    monkeypatch.setattr(dependencies.settings, "API_KEY", "test-only-api-key")
    app = FastAPI()

    # Exercise FastAPI's real auth dependency without importing external services.
    @app.get("/protected", dependencies=[Depends(dependencies.verify_api_access)])
    def protected():
        return {"status": "ok"}

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-API-KEY": "wrong-api-key"}],
    ids=["missing-credentials", "wrong-api-key-without-token"],
)
def test_rejects_request_without_valid_credentials(client, headers):
    response = client.get("/protected", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_accepts_valid_api_key(client):
    response = client.get("/protected", headers={"X-API-KEY": "test-only-api-key"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
