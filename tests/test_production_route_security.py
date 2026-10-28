import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.security import create_key
from app.agent_gateway import provision_agent

client = TestClient(app)


@pytest.fixture
def credentials(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "route_security.db"),
    )
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    initialize()

    with connect() as db:
        business_id = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Oak Valley",),
        ).lastrowid

    owner = create_key(business_id)
    agent = provision_agent(
        business_id,
        "Leadkeeper",
        ["jobs:work", "proposals:create"],
    )

    return owner, agent["token"]


def test_agent_can_create_job(credentials):
    _, token = credentials

    response = client.post(
        "/api/workstation/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "kind": "lead:analyze",
            "instructions": {"lead_id": 1},
        },
    )

    assert response.status_code == 201


def test_anonymous_cannot_create_job(credentials):
    response = client.post(
        "/api/workstation/jobs",
        json={
            "kind": "lead:analyze",
            "instructions": {"lead_id": 1},
        },
    )

    assert response.status_code == 401


def test_agent_can_submit_proposal(credentials):
    _, token = credentials

    response = client.post(
        "/api/approvals/proposals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "action": "outreach:draft",
            "title": "Follow up",
            "payload": {"message": "Hello"},
        },
    )

    assert response.status_code == 201


def test_agent_cannot_review_owner_proposals(credentials):
    _, token = credentials

    response = client.get(
        "/api/approvals",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_owner_can_review_proposals(credentials):
    owner, _ = credentials

    response = client.get(
        "/api/approvals",
        headers={"X-API-Key": owner},
    )

    assert response.status_code == 200


def test_login_reaches_credential_validation(credentials):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "nobody",
            "password": "incorrect",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
