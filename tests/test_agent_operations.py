from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.auth import create_user
from app.agent_gateway import provision_agent


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "operations.db"),
    )
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")
    initialize()

    with connect() as db:
        oak = db.execute(
            "INSERT INTO businesses(name) VALUES ('Oak')"
        ).lastrowid
        pine = db.execute(
            "INSERT INTO businesses(name) VALUES ('Pine')"
        ).lastrowid

    create_user(oak, "oak-ops", "secure-password-123")
    create_user(pine, "pine-ops", "secure-password-456")

    worker = provision_agent(
        oak, "Oak Worker", ["jobs:work"]
    )
    provision_agent(
        pine, "Pine Worker", ["jobs:work"]
    )

    oak_client = TestClient(
        app, base_url="https://testserver"
    )
    pine_client = TestClient(
        app, base_url="https://testserver"
    )

    for client, username, password in (
        (oak_client, "oak-ops", "secure-password-123"),
        (pine_client, "pine-ops", "secure-password-456"),
    ):
        assert client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password,
            },
        ).status_code == 200

    return oak_client, pine_client, worker


def test_login_required(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    guest = TestClient(
        app, base_url="https://testserver"
    )

    assert guest.get(
        "/api/customer/operations"
    ).status_code == 401


def test_agent_list_is_tenant_scoped(tmp_path, monkeypatch):
    oak, pine, _ = setup(tmp_path, monkeypatch)

    oak_data = oak.get(
        "/api/customer/operations"
    ).json()

    pine_data = pine.get(
        "/api/customer/operations"
    ).json()

    assert [a["name"] for a in oak_data["agents"]] == [
        "Oak Worker"
    ]
    assert [a["name"] for a in pine_data["agents"]] == [
        "Pine Worker"
    ]


def test_job_status_counts(tmp_path, monkeypatch):
    oak, pine, worker = setup(tmp_path, monkeypatch)

    created = oak.post(
        "/api/customer/jobs",
        json={
            "agent_id": worker["agent_id"],
            "kind": "lead:analyze",
            "instructions": "Review lead",
        },
    )

    assert created.status_code == 201

    data = oak.get(
        "/api/customer/operations"
    ).json()

    assert data["summary"]["queued"] == 1
    assert data["summary"]["working"] == 0
    assert data["summary"]["completed"] == 0
    assert len(data["jobs"]) == 1

    other = pine.get(
        "/api/customer/operations"
    ).json()

    assert other["summary"]["queued"] == 0
    assert other["jobs"] == []


def test_monitor_excludes_tokens(tmp_path, monkeypatch):
    oak, _, _ = setup(tmp_path, monkeypatch)

    response = oak.get("/api/customer/operations")

    assert response.status_code == 200
    assert "token_hash" not in response.text
    assert '"token"' not in response.text


def test_monitor_limit_validated(tmp_path, monkeypatch):
    oak, _, _ = setup(tmp_path, monkeypatch)

    assert oak.get(
        "/api/customer/operations?limit=101"
    ).status_code == 422
