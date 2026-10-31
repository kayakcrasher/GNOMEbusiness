"""Production authentication regression coverage."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.production_guard import validate_production_config


@pytest.fixture
def secure_client(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH", str(tmp_path / "secure.db")
    )
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    initialize()

    with connect() as db:
        db.execute(
            "INSERT INTO businesses (name) VALUES (?)",
            ("Oak Workshop",),
        )

    return TestClient(app)


def test_production_requires_authentication(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "0")

    with pytest.raises(
        RuntimeError, match="requires authentication"
    ):
        validate_production_config()


def test_production_configuration_valid(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    assert validate_production_config() is True


def test_health_remains_public(secure_client):
    response = secure_client.get("/api/health")
    assert response.status_code == 200


def test_leads_require_authentication(secure_client):
    response = secure_client.get(
        "/api/businesses/1/leads"
    )
    assert response.status_code == 401


def test_creation_requires_authentication(secure_client):
    response = secure_client.post(
        "/api/leads",
        json={
            "business_id": 1,
            "company": "Unauthorized Business",
        },
    )
    assert response.status_code == 401


def test_owner_approvals_require_authentication(secure_client):
    response = secure_client.get("/api/approvals")
    assert response.status_code == 401


def test_agent_cannot_decide_without_owner_key(secure_client):
    response = secure_client.post(
        "/api/approvals/1/decision",
        json={"decision": "approved"},
    )
    assert response.status_code == 401


def test_agent_status_requires_token(secure_client):
    response = secure_client.get(
        "/api/approvals/agent/1"
    )
    assert response.status_code == 401


def test_business_creation_not_public(secure_client):
    response = secure_client.post(
        "/api/businesses",
        json={"name": "Unauthorized"},
    )
    assert response.status_code == 403


def test_invalid_environment_rejected(monkeypatch):
    monkeypatch.setenv("GNOME_ENV", "unsafe")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    with pytest.raises(RuntimeError):
        validate_production_config()
