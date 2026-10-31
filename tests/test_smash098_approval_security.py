"""Real production-mode approval authorization tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.security import create_key
from app.agent_gateway import provision_agent


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH", str(tmp_path / "approval098.db")
    )
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    initialize()

    with connect() as db:
        oak = db.execute(
            "INSERT INTO businesses(name) VALUES ('Oak')"
        ).lastrowid
        pine = db.execute(
            "INSERT INTO businesses(name) VALUES ('Pine')"
        ).lastrowid

    oak_agent = provision_agent(
        oak, "Oak Agent", ["proposals:create"]
    )
    other_agent = provision_agent(
        oak, "Other Oak Agent", ["proposals:create"]
    )
    pine_agent = provision_agent(
        pine, "Pine Agent", ["proposals:create"]
    )

    client = TestClient(app)
    submitted = client.post(
        "/api/approvals/proposals",
        headers={
            "Authorization": f'Bearer {oak_agent["token"]}'
        },
        json={
            "action": "outreach:draft",
            "title": "Review introduction",
            "payload": {"body": "Hello"},
            "idempotency_key": "smash098-oak-1",
        },
    )
    assert submitted.status_code == 201, submitted.text

    return {
        "client": client,
        "id": submitted.json()["id"],
        "oak_key": create_key(oak),
        "pine_key": create_key(pine),
        "oak_agent": oak_agent["token"],
        "other_agent": other_agent["token"],
        "pine_agent": pine_agent["token"],
    }


def agent_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_owner_can_review(setup):
    s = setup
    response = s["client"].get(
        "/api/approvals",
        headers={"X-API-Key": s["oak_key"]},
    )
    assert response.status_code == 200
    assert any(
        p["id"] == s["id"]
        for p in response.json()["proposals"]
    )


def test_other_customer_cannot_see_proposal(setup):
    s = setup
    response = s["client"].get(
        "/api/approvals",
        headers={"X-API-Key": s["pine_key"]},
    )
    assert response.status_code == 200
    assert all(
        p["id"] != s["id"]
        for p in response.json()["proposals"]
    )


def test_other_customer_cannot_decide(setup):
    s = setup
    response = s["client"].post(
        f'/api/approvals/{s["id"]}/decision',
        headers={"X-API-Key": s["pine_key"]},
        json={"decision": "approved"},
    )
    assert response.status_code == 404


def test_agent_cannot_approve(setup):
    s = setup
    response = s["client"].post(
        f'/api/approvals/{s["id"]}/decision',
        headers=agent_headers(s["oak_agent"]),
        json={"decision": "approved"},
    )
    assert response.status_code == 401


def test_own_agent_can_read_status(setup):
    s = setup
    response = s["client"].get(
        f'/api/approvals/agent/{s["id"]}',
        headers=agent_headers(s["oak_agent"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["executed"] is False


@pytest.mark.parametrize(
    "token_name",
    ["other_agent", "pine_agent"],
)
def test_other_agents_cannot_read_status(setup, token_name):
    s = setup
    response = s["client"].get(
        f'/api/approvals/agent/{s["id"]}',
        headers=agent_headers(s[token_name]),
    )
    assert response.status_code == 404


def test_missing_agent_token_rejected(setup):
    s = setup
    response = s["client"].get(
        f'/api/approvals/agent/{s["id"]}'
    )
    assert response.status_code == 401


def test_customer_can_approve_once(setup):
    s = setup
    url = f'/api/approvals/{s["id"]}/decision'
    headers = {"X-API-Key": s["oak_key"]}

    first = s["client"].post(
        url, headers=headers,
        json={"decision": "approved"},
    )
    second = s["client"].post(
        url, headers=headers,
        json={"decision": "rejected"},
    )

    assert first.status_code == 200
    assert first.json()["executed"] is False
    assert second.status_code == 409

    status = s["client"].get(
        f'/api/approvals/agent/{s["id"]}',
        headers=agent_headers(s["oak_agent"]),
    )
    assert status.status_code == 200
    assert status.json()["status"] == "approved"

    with connect() as db:
        events = db.execute(
            """
            SELECT event FROM approval_events
            WHERE proposal_id = ?
            ORDER BY id
            """,
            (s["id"],),
        ).fetchall()

    assert [row["event"] for row in events] == [
        "submitted", "approved"
    ]
