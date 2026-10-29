import pytest

from app.production_guard import (
    validate_production_config,
)


def test_missing_environment_is_production(monkeypatch):
    monkeypatch.delenv("GNOME_ENV", raising=False)
    monkeypatch.delenv(
        "GNOME_ENFORCE_AUTH", raising=False
    )

    assert validate_production_config()


def test_production_rejects_disabled_auth(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "0")

    with pytest.raises(RuntimeError):
        validate_production_config()


def test_invalid_environment_rejected(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "staging")

    with pytest.raises(RuntimeError):
        validate_production_config()


def test_invalid_auth_setting_rejected(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "maybe")

    with pytest.raises(RuntimeError):
        validate_production_config()


def test_explicit_development_mode(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "development")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "0")

    assert validate_production_config()
