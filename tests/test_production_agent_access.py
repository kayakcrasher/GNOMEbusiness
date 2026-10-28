import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.security import create_key
from app.agent_gateway import provision_agent

client = TestClient(app)


@pytest.fixture
def tenant(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "production_access.db"),
    )
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    initialize()

    with connect() as db:
        business_id = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Oak Valley",),
        ).lastrowid

    owner_key = create_key(business_id)
    agent = provision_agent(
        business_id,
        "Leadkeeper",
        ["leads:read"],
    )

    return business_id, owner_key, agent["token"]


def test_agent_bearer_access_in_production(tenant):
    _, _, token = tenant

    response = client.get(
        "/api/agents/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_agent_cannot_use_owner_endpoint(tenant):
    business_id, _, token = tenant

    response = client.get(
        f"/api/businesses/{business_id}/leads",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_owner_key_still_works(tenant):
    business_id, key, _ = tenant

    response = client.get(
        f"/api/businesses/{business_id}/leads",
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200


def test_anonymous_agent_access_denied(tenant):
    response = client.get("/api/agents/me")
    assert response.status_code == 401
