import socket
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from fastapi.testclient import TestClient


TEST_SETTINGS = {
    "ENV": "development",
    "DEBUG": "false",
    "API_KEY": "test-only-api-key",
    "JWT_SECRET_KEY": "test-only-jwt-secret-for-api-tests",
    "JWT_ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "CORS_ORIGINS": "http://localhost:8501,http://127.0.0.1:8501,http://localhost:8000,http://127.0.0.1:8000",
    "SUPABASE_URL": "https://supabase.invalid",
    "SUPABASE_KEY": "test-only-supabase-key",
    "REDIS_URL": "redis://redis.invalid:6379/0",
}


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch, tmp_path):
    # Settings read relative to an empty directory, never the checkout's .env.
    monkeypatch.chdir(tmp_path)
    for name, value in TEST_SETTINGS.items():
        monkeypatch.setenv(name, value)

    def reject_network(*args, **kwargs):
        raise AssertionError("Network access is forbidden in tests")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket, "getaddrinfo", reject_network)


@pytest.fixture
def api(monkeypatch):
    database = Mock()
    redis_client = Mock()
    redis_client.get.return_value = None
    monkeypatch.setattr("supabase.create_client", Mock(return_value=database))
    monkeypatch.setattr("redis.from_url", Mock(return_value=redis_client))

    preprocessor = Mock()
    preprocessor.transform.return_value = np.array([[250000.0]])
    preprocessor.get_feature_names_out.return_value = ["num__grossapproval"]
    model = Mock()
    model.predict_proba.return_value = np.array([[0.8, 0.2]])
    model.named_steps = {"preprocessor": preprocessor, "classifier": Mock()}
    monkeypatch.setattr("joblib.load", Mock(return_value=model))

    explainer = Mock(return_value=SimpleNamespace(
        base_values=np.array([0.1]), values=np.array([[0.1]])
    ))
    monkeypatch.setattr("shap.TreeExplainer", Mock(return_value=explainer))

    from app.core.config import settings

    # Reapply values when another test has already imported the settings module.
    for name, value in TEST_SETTINGS.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

    from app.api import routes_auth, routes_predict
    from app.cache.redis_cache import cache
    from app.main import app

    monkeypatch.setattr(routes_auth, "supabase_client", database)
    monkeypatch.setattr(routes_predict, "supabase_client", database)
    monkeypatch.setattr(routes_predict, "MODEL", model)
    monkeypatch.setattr(routes_predict, "_explainer", None)
    monkeypatch.setattr(cache, "client", redis_client)
    monkeypatch.setattr(cache, "is_connected", True)

    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client, model=model, database=database, redis=redis_client
        )


@pytest.fixture
def loan_application():
    return {
        "grossapproval": 250000.0,
        "sbaguaranteedapproval": 187500.0,
        "terminmonths": 120,
        "initialinterestrate": 7.5,
        "jobssupported": 10,
        "bank_prior_def_rate": 0.08,
        "bank_prior_loans": 500.0,
        "sector_historical_default_rate": 0.087,
        "naics_sector": "72",
        "businesstype": "CORPORATION",
        "business_age_group": "Existing",
        "bank_experience_tier": "High",
        "revolverstatus": 0,
        "is_same_state_bank": 1,
        "is_variable_rate": 1,
        "is_franchise": 0,
        "collateralind": 1,
    }
