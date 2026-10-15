import importlib.util
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from threadpoolctl import threadpool_limits


AUTH_HEADERS = {"X-API-KEY": "test-only-api-key"}


def test_cache_hit_skips_inference_and_still_audits(api, loan_application):
    first = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert first.status_code == 200
    first_key, payload = api.redis.set.call_args.args
    api.redis.get.return_value = payload.encode("utf-8")
    second = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert second.status_code == 200
    assert second.json() == first.json()
    api.model.predict_proba.assert_called_once()
    assert api.redis.get.call_args.args[0] == first_key
    assert api.database.table.return_value.insert.call_count == 2


def test_corrupt_cache_entry_falls_back_to_inference(api, loan_application, caplog):
    api.redis.get.return_value = b"not valid JSON"
    response = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["expected_loss"] == 12500.0
    api.model.predict_proba.assert_called_once()
    assert "Failed to query Redis cache" in caplog.text


def test_cache_key_failure_does_not_block_prediction(api, loan_application, monkeypatch, caplog):
    monkeypatch.setattr("app.api.routes_predict.hashlib.md5", Mock(side_effect=ValueError("digest unavailable")))
    response = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["expected_loss"] == 12500.0
    api.redis.get.assert_not_called()
    api.redis.set.assert_not_called()
    assert "digest unavailable" in caplog.text


@pytest.mark.parametrize("operation", ["get", "set"])
def test_cache_adapter_failure_does_not_block_prediction(api, loan_application, monkeypatch, caplog, operation):
    monkeypatch.setattr(f"app.api.routes_predict.cache.{operation}", Mock(side_effect=RuntimeError("cache adapter unavailable")))
    response = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["expected_loss"] == 12500.0
    api.model.predict_proba.assert_called_once()
    assert "cache adapter unavailable" in caplog.text


def test_audit_failure_does_not_block_prediction(api, loan_application, caplog):
    api.database.table.return_value.insert.return_value.execute.side_effect = RuntimeError("audit unavailable")
    response = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["expected_loss"] == 12500.0
    assert "Failed to log prediction to Supabase: audit unavailable" in caplog.text


def test_unconfigured_audit_skips_database(api, loan_application, monkeypatch):
    monkeypatch.setattr("app.api.routes_predict.supabase_client", None)
    response = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert response.status_code == 200
    api.database.table.assert_not_called()


@pytest.mark.parametrize("pd_score,tier,action", [
    (0.05, "Tier 1", "Auto Approve"),
    (0.10, "Tier 2", "Manual Review"),
    (0.249, "Tier 2", "Manual Review"),
    (0.25, "Tier 3", "Senior Review"),
    (0.399, "Tier 3", "Senior Review"),
    (0.40, "Tier 4", "Recommend Denial"),
    (0.99, "Tier 4", "Recommend Denial"),
])
def test_serving_risk_tier_boundaries(api, loan_application, pd_score, tier, action):
    api.model.predict_proba.return_value = np.array([[1 - pd_score, pd_score]])
    response = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert response.status_code == 200
    result = response.json()
    assert result["risk_tier"] == tier
    assert result["underwriting_action"] == action
    assert result["expected_loss"] == pytest.approx(pd_score * 62500)


@pytest.mark.parametrize("module_name", ["routes_auth", "routes_predict"])
def test_failed_database_initialization_disables_client(api, monkeypatch, caplog, module_name):
    monkeypatch.setattr("supabase.create_client", Mock(side_effect=RuntimeError("client initialization unavailable")))
    path = Path(__file__).resolve().parents[1] / "app/api" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"{module_name}_startup_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.supabase_client is None
    assert "client initialization unavailable" in caplog.text


def test_bundled_model_and_real_shap_explainer_serve_offline(api, loan_application, monkeypatch):
    from app.api import routes_predict

    path = Path(__file__).resolve().parents[1] / "app/models/best_hgb_pipeline.pkl"
    with threadpool_limits(limits=1):
        monkeypatch.setattr(routes_predict, "MODEL", api.real_model_loader(path))
        monkeypatch.setattr(routes_predict.shap, "TreeExplainer", api.real_explainer_factory)
        response = api.client.post("/predict", json=loan_application, headers=AUTH_HEADERS)
    assert response.status_code == 200
    result = response.json()
    assert 0 < result["probability_of_default"] < 1
    assert result["expected_loss"] == pytest.approx(result["probability_of_default"] * 62500)
    assert len(result["shap_values"]) > 1
    assert result["shap_values"].keys() == result["processed_features"].keys()
    raw_score = result["shap_base_value"] + sum(result["shap_values"].values())
    assert 1 / (1 + np.exp(-raw_score)) == pytest.approx(result["probability_of_default"], abs=1e-6)
