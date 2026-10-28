from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.agent_gateway import provision_agent
from app.security import create_key

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "approvals.db"),
    )
    monkeypatch.delenv(
        "GNOME_ENFORCE_AUTH",
        raising=False,
    )

    initialize()

    with connect() as db:
        oak = db.execute(
            "INSERT INTO businesses(name) VALUES ('Oak')"
        ).lastrowid

        pine = db.execute(
            "INSERT INTO businesses(name) VALUES ('Pine')"
        ).lastrowid

    agent = provision_agent(
        oak,
        "Leadkeeper",
        ["proposals:create"],
    )

    return {
        "oak": create_key(oak),
        "pine": create_key(pine),
        "agent": agent["token"],
    }


def submit(keys):
    return client.post(
        "/api/approvals/proposals",
        headers={
            "Authorization": "Bearer " + keys["agent"]
        },
        json={
            "action": "outreach:draft",
            "title": "Prepare prospect introduction",
            "payload": {
                "subject": "Introduction",
                "body": "Hello, we'd like to connect.",
            },
        },
    )


def test_agent_can_propose(tmp_path, monkeypatch):
    keys = seed(tmp_path, monkeypatch)

    response = submit(keys)

    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_agent_cannot_approve(tmp_path, monkeypatch):
    keys = seed(tmp_path, monkeypatch)
    proposal_id = submit(keys).json()["id"]

    response = client.post(
        f"/api/approvals/{proposal_id}/decision",
        headers={
            "Authorization": "Bearer " + keys["agent"]
        },
        json={"decision": "approved"},
    )

    assert response.status_code == 401


def test_client_can_approve(tmp_path, monkeypatch):
    keys = seed(tmp_path, monkeypatch)
    proposal_id = submit(keys).json()["id"]

    response = client.post(
        f"/api/approvals/{proposal_id}/decision",
        headers={"X-API-Key": keys["oak"]},
        json={"decision": "approved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["executed"] is False


def test_other_client_cannot_approve(
    tmp_path, monkeypatch
):
    keys = seed(tmp_path, monkeypatch)
    proposal_id = submit(keys).json()["id"]

    response = client.post(
        f"/api/approvals/{proposal_id}/decision",
        headers={"X-API-Key": keys["pine"]},
        json={"decision": "approved"},
    )

    assert response.status_code == 404


def test_double_approval_blocked(
    tmp_path, monkeypatch
):
    keys = seed(tmp_path, monkeypatch)
    proposal_id = submit(keys).json()["id"]

    headers = {"X-API-Key": keys["oak"]}

    first = client.post(
        f"/api/approvals/{proposal_id}/decision",
        headers=headers,
        json={"decision": "approved"},
    )

    second = client.post(
        f"/api/approvals/{proposal_id}/decision",
        headers=headers,
        json={"decision": "approved"},
    )

    assert first.status_code == 200
    assert second.status_code == 409
