def test_disallowed_origin_has_no_cors_access_header(api):
    response = api.client.get("/health", headers={"Origin": "https://untrusted.invalid"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_disallowed_preflight_is_rejected(api):
    response = api.client.options("/predict", headers={
        "Origin": "https://untrusted.invalid",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "X-API-KEY,Content-Type",
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
