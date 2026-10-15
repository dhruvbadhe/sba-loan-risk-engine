import logging

CREDENTIALS = {"username": "test-user", "password": "test-password"}


def test_signup_requires_configured_database(api, monkeypatch):
    monkeypatch.setattr("app.api.routes_auth.supabase_client", None)
    response = api.client.post("/signup", json=CREDENTIALS)
    assert response.status_code == 503
    api.database.table.assert_not_called()


def test_signup_hashes_password_before_insert(api):
    from app.core.security import verify_password

    api.database.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    response = api.client.post("/signup", json=CREDENTIALS)
    assert response.status_code == 201
    assert response.json() == {"message": "User registered successfully."}
    api.database.table.assert_any_call("users")
    saved = api.database.table.return_value.insert.call_args.args[0]
    assert saved["username"] == CREDENTIALS["username"]
    assert saved["password_hash"] != CREDENTIALS["password"]
    assert verify_password(CREDENTIALS["password"], saved["password_hash"])


def test_duplicate_signup_does_not_insert(api):
    api.database.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"username": "test-user"}]
    response = api.client.post("/signup", json=CREDENTIALS)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists."
    api.database.table.return_value.insert.assert_not_called()


def test_signup_query_failure_is_generic_and_does_not_insert(api, caplog):
    api.database.table.return_value.select.return_value.eq.return_value.execute.side_effect = RuntimeError("query unavailable")
    with caplog.at_level(logging.ERROR, logger="app"):
        response = api.client.post("/signup", json=CREDENTIALS)
    assert response.status_code == 500
    assert response.json()["detail"] == "Database error."
    assert "query unavailable" in caplog.text
    api.database.table.return_value.insert.assert_not_called()


def test_signup_insert_failure_is_generic(api, caplog):
    api.database.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    api.database.table.return_value.insert.return_value.execute.side_effect = RuntimeError("insert unavailable")
    with caplog.at_level(logging.ERROR, logger="app"):
        response = api.client.post("/signup", json=CREDENTIALS)
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create user."
    assert "insert unavailable" in caplog.text


def test_login_query_failure_is_generic(api):
    api.database.table.return_value.select.return_value.eq.return_value.execute.side_effect = RuntimeError("private database detail")
    response = api.client.post("/login", data=CREDENTIALS)
    assert response.status_code == 500
    assert response.json()["detail"] == "Database verification error."
    assert "private database detail" not in response.text


def test_unknown_user_cannot_log_in(api):
    api.database.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    response = api.client.post("/login", data=CREDENTIALS)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
    assert response.headers["www-authenticate"] == "Bearer"


def test_wrong_password_cannot_log_in(api):
    from app.core.security import get_password_hash

    api.database.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"password_hash": get_password_hash("different-password")}
    ]
    response = api.client.post("/login", data=CREDENTIALS)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
    assert response.headers["www-authenticate"] == "Bearer"
