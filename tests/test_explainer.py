def test_two_uncached_requests_reuse_one_explainer(api, loan_application):
    from app.api import routes_predict

    factory = routes_predict.shap.TreeExplainer
    first = api.client.post("/predict", json=loan_application, headers={"X-API-KEY": "test-only-api-key"})
    second = api.client.post("/predict", json={**loan_application, "grossapproval": 300000.0},
                             headers={"X-API-KEY": "test-only-api-key"})

    assert first.status_code == second.status_code == 200
    assert api.model.predict_proba.call_count == 2
    factory.assert_called_once_with(api.model.named_steps["classifier"])
    assert factory.return_value.call_count == 2
