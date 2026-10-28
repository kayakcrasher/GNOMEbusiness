from fastapi.testclient import TestClient

from app.main import app
from app.database import connect
from tests.test_approvals import seed

client = TestClient(app)


def submit(token, key, message="Need a quote"):
    return client.post(
        "/api/approvals/proposals",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "action": "lead:review",
            "title": "Leadkeeper workflow review",
            "idempotency_key": key,
            "payload": {
                "job_id": 47,
                "message": message,
            },
        },
    )


def test_retry_returns_same_proposal(tmp_path, monkeypatch):
    keys = seed(tmp_path, monkeypatch)

    first = submit(keys["agent"], "job:47")
    second = submit(keys["agent"], "job:47")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    with connect() as db:
        count = db.execute(
            "SELECT COUNT(*) AS n FROM agent_proposals"
        ).fetchone()["n"]

        events = db.execute(
            "SELECT COUNT(*) AS n FROM approval_events"
        ).fetchone()["n"]

    assert count == 1
    assert events == 1


def test_changed_payload_conflicts(tmp_path, monkeypatch):
    keys = seed(tmp_path, monkeypatch)

    assert submit(
        keys["agent"], "job:47"
    ).status_code == 201

    changed = submit(
        keys["agent"], "job:47", "Different request"
    )

    assert changed.status_code == 409


def test_distinct_keys_create_distinct_proposals(
    tmp_path, monkeypatch
):
    keys = seed(tmp_path, monkeypatch)

    first = submit(keys["agent"], "job:47")
    second = submit(keys["agent"], "job:48")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_existing_schema_migrates(tmp_path, monkeypatch):
    keys = seed(tmp_path, monkeypatch)

    from app.approvals import migrate

    migrate()

    with connect() as db:
        columns = {
            row["name"]
            for row in db.execute(
                "PRAGMA table_info(agent_proposals)"
            )
        }

    assert "idempotency_key" in columns
