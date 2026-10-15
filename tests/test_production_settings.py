import os
from pathlib import Path
import subprocess
import sys

import pytest


TEST_SECRETS = {
    "API_KEY": "test-only-api-key-for-production-validation",
    "JWT_SECRET_KEY": "test-only-jwt-key-for-production-validation",
}
DEFAULT_SECRETS = {
    "API_KEY": "dev-key-change-in-production",
    "JWT_SECRET_KEY": "super-secret-key-change-for-production",
}


def load_startup_settings(tmp_path, environment, secrets):
    # A new process exercises the settings instance created during app startup.
    # Its empty working directory and minimal environment isolate it from .env.
    env = {
        "PATH": os.defpath,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        "ENV": environment,
        **secrets,
    }
    # Preserve only coverage instrumentation when measuring these child processes.
    if "COVERAGE_PROCESS_CONFIG" in os.environ:
        env["COVERAGE_PROCESS_CONFIG"] = os.environ["COVERAGE_PROCESS_CONFIG"]
    script = """
import socket

def reject_network(*args, **kwargs):
    raise AssertionError("Network access is forbidden in settings tests")

socket.socket.connect = reject_network
socket.socket.connect_ex = reject_network
socket.create_connection = reject_network

from app.core.config import settings
print("Settings loaded")
"""
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.mark.parametrize("name", ["API_KEY", "JWT_SECRET_KEY"])
@pytest.mark.parametrize("invalid_value", [None, "default", "", "   "],
                         ids=["missing", "default", "empty", "whitespace"])
def test_production_rejects_unsafe_secret(tmp_path, name, invalid_value):
    secrets = dict(TEST_SECRETS)
    if invalid_value is None:
        del secrets[name]
    else:
        secrets[name] = DEFAULT_SECRETS[name] if invalid_value == "default" else invalid_value

    result = load_startup_settings(tmp_path, "production", secrets)

    assert result.returncode != 0
    assert f"{name} must be set to a non-default value in production" in result.stderr
    assert "Settings loaded" not in result.stdout
    for value in TEST_SECRETS.values():
        assert value not in result.stderr


def test_production_rejects_both_defaults(tmp_path):
    result = load_startup_settings(tmp_path, "production", {})

    assert result.returncode != 0
    assert "must be set to a non-default value in production" in result.stderr


def test_production_accepts_explicit_secrets(tmp_path):
    result = load_startup_settings(tmp_path, "production", TEST_SECRETS)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Settings loaded"


def test_development_accepts_defaults(tmp_path):
    result = load_startup_settings(tmp_path, "development", {})

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Settings loaded"
