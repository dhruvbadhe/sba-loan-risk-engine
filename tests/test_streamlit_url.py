from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize(
    "configured,expected",
    [
        ("http://127.0.0.1:8000", "http://127.0.0.1:8000/login"),
        (None, "https://sba-loan-risk-api.onrender.com/login"),
    ],
)
def test_login_uses_configured_backend(monkeypatch, configured, expected):
    if configured is None:
        monkeypatch.delenv("API_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("API_BASE_URL", configured)
    post = Mock(return_value=Mock(status_code=401))
    monkeypatch.setattr("requests.post", post)
    script = Path(__file__).resolve().parents[1] / "app/streamlit_app.py"
    app = AppTest.from_file(str(script)).run(timeout=15)
    assert not app.exception
    app.text_input(key="login_user").set_value("test-user")
    app.text_input(key="login_pass").set_value("test-password")
    app.button[0].click().run(timeout=15)
    assert not app.exception
    post.assert_called_once_with(
        expected,
        data={"username": "test-user", "password": "test-password"},
        timeout=60.0,
    )
