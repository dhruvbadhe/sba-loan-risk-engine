from datetime import timedelta

import pytest


@pytest.mark.parametrize(
    "credentials",
    ["missing", "wrong-api-key", "bad-jwt", "expired-jwt"],
)
def test_predict_rejects_invalid_credentials(api, loan_application, credentials):
    from app.core.security import create_access_token

    headers = {}
    if credentials == "wrong-api-key":
        headers["X-API-KEY"] = "wrong-test-api-key"
    elif credentials == "bad-jwt":
        headers["Authorization"] = "Bearer invalid.jwt.token"
    elif credentials == "expired-jwt":
        token = create_access_token(
            {"sub": "test-user"}, expires_delta=timedelta(minutes=-1)
        )
        headers["Authorization"] = f"Bearer {token}"

    response = api.client.post("/predict", json=loan_application, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    api.model.predict_proba.assert_not_called()
    api.redis.get.assert_not_called()
    api.database.table.assert_not_called()


@pytest.mark.parametrize("auth_method", ["jwt", "api-key"])
def test_predict_accepts_valid_credentials(api, loan_application, auth_method):
    from app.core.security import create_access_token

    if auth_method == "jwt":
        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}
        expected_user = "test-user"
    else:
        headers = {"X-API-KEY": "test-only-api-key"}
        expected_user = "API_KEY_USER"

    response = api.client.post("/predict", json=loan_application, headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "probability_of_default": 0.2,
        "loss_given_default": 0.25,
        "exposure_at_default": 250000.0,
        "expected_loss": 12500.0,
        "risk_tier": "Tier 2",
        "underwriting_action": "Manual Review",
        "shap_base_value": 0.1,
        "shap_values": {"num__grossapproval": 0.1},
        "processed_features": {"num__grossapproval": 250000.0},
    }
    api.model.predict_proba.assert_called_once()
    api.redis.get.assert_called_once()
    api.redis.set.assert_called_once()
    api.database.table.assert_called_once_with("predictions")
    api.database.table.return_value.insert.assert_called_once_with(
        {
            "username": expected_user,
            "loan_amount": 250000.0,
            "term_months": 120,
            "interest_rate": 7.5,
            "probability_of_default": 0.2,
            "expected_loss": 12500.0,
            "risk_tier": "Tier 2",
        }
    )
    api.database.table.return_value.insert.return_value.execute.assert_called_once()


@pytest.mark.parametrize("invalid_field", ["missing-amount", "non-numeric-amount"])
def test_predict_rejects_invalid_payload(api, loan_application, invalid_field):
    if invalid_field == "missing-amount":
        del loan_application["grossapproval"]
    else:
        loan_application["grossapproval"] = "not-a-number"

    response = api.client.post(
        "/predict", json=loan_application, headers={"X-API-KEY": "test-only-api-key"}
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "grossapproval"]
    api.model.predict_proba.assert_not_called()
    api.redis.get.assert_not_called()
    api.database.table.assert_not_called()


def test_health_is_public(api):
    response = api.client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}
    api.model.predict_proba.assert_not_called()
    api.redis.get.assert_not_called()
    api.database.table.assert_not_called()
