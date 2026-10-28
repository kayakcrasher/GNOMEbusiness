import pytest

from app.production_guard import (
    validate_production_config,
)


def test_development_allows_auth_disabled(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "development")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "0")

    assert validate_production_config()


def test_production_requires_auth(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.delenv("GNOME_ENFORCE_AUTH", raising=False)

    with pytest.raises(RuntimeError):
        validate_production_config()


def test_production_rejects_disabled_auth(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "0")

    with pytest.raises(RuntimeError):
        validate_production_config()


def test_production_accepts_enforced_auth(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    assert validate_production_config()
