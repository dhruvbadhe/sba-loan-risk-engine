def test_signup_examples_use_supported_openapi_schema(api):
    response = api.client.get("/openapi.json")
    assert response.status_code == 200
    properties = response.json()["components"]["schemas"]["UserCreate"]["properties"]
    assert properties["username"]["examples"] == ["dhruv"]
    assert properties["password"]["examples"] == ["mypassword123"]
