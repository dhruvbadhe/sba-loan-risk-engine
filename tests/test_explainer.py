from concurrent.futures import ThreadPoolExecutor
import time

import pytest


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




def test_concurrent_initialization_builds_only_one_explainer(api):
    from app.api import routes_predict

    shared = object()

    def build(classifier):
        # Let competing threads attempt initialization while construction runs.
        time.sleep(0.02)
        return shared

    routes_predict.shap.TreeExplainer.side_effect = build
    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(workers.map(lambda _: routes_predict.get_explainer(), range(8)))
    assert all(result is shared for result in results)
    routes_predict.shap.TreeExplainer.assert_called_once()


def test_failed_explainer_initialization_can_retry(api):
    from app.api import routes_predict

    shared = object()
    factory = routes_predict.shap.TreeExplainer
    factory.side_effect = [RuntimeError("explainer unavailable"), shared]
    with pytest.raises(RuntimeError, match="explainer unavailable"):
        routes_predict.get_explainer()
    assert routes_predict.get_explainer() is shared
    assert routes_predict.get_explainer() is shared
    assert factory.call_count == 2
