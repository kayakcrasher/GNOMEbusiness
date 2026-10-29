from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.auth import create_user
from app.agent_gateway import provision_agent


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "customer_jobs.db"),
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

    create_user(oak, "oak-jobs", "secure-password-123")
    create_user(pine, "pine-jobs", "secure-password-456")

    worker = provision_agent(
        oak, "Worker", ["jobs:work"]
    )
    reader = provision_agent(
        oak, "Reader", ["leads:read"]
    )
    outsider = provision_agent(
        pine, "Other Worker", ["jobs:work"]
    )

    oak_client = TestClient(
        app, base_url="https://testserver"
    )
    pine_client = TestClient(
        app, base_url="https://testserver"
    )

    for client, username, password in (
        (oak_client, "oak-jobs", "secure-password-123"),
        (pine_client, "pine-jobs", "secure-password-456"),
    ):
        response = client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password,
            },
        )
        assert response.status_code == 200

    return oak_client, pine_client, worker, reader, outsider


def payload(agent_id):
    return {
        "agent_id": agent_id,
        "kind": "lead:analyze",
        "instructions": "Review the newest lead",
    }


def test_login_required(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    guest = TestClient(
        app, base_url="https://testserver"
    )

    assert guest.get(
        "/api/customer/jobs"
    ).status_code == 401


def test_customer_queues_job(tmp_path, monkeypatch):
    oak, _, worker, _, _ = setup(tmp_path, monkeypatch)

    response = oak.post(
        "/api/customer/jobs",
        json=payload(worker["agent_id"]),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"

    jobs = oak.get("/api/customer/jobs").json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["instructions"]["request"] == (
        "Review the newest lead"
    )


def test_other_tenant_agent_denied(tmp_path, monkeypatch):
    oak, _, _, _, outsider = setup(
        tmp_path, monkeypatch
    )

    response = oak.post(
        "/api/customer/jobs",
        json=payload(outsider["agent_id"]),
    )

    assert response.status_code == 404


def test_agent_requires_work_scope(tmp_path, monkeypatch):
    oak, _, _, reader, _ = setup(
        tmp_path, monkeypatch
    )

    response = oak.post(
        "/api/customer/jobs",
        json=payload(reader["agent_id"]),
    )

    assert response.status_code == 403


def test_jobs_are_tenant_scoped(tmp_path, monkeypatch):
    oak, pine, worker, _, _ = setup(
        tmp_path, monkeypatch
    )

    assert oak.post(
        "/api/customer/jobs",
        json=payload(worker["agent_id"]),
    ).status_code == 201

    assert pine.get(
        "/api/customer/jobs"
    ).json()["jobs"] == []


def test_unsupported_job_rejected(tmp_path, monkeypatch):
    oak, _, worker, _, _ = setup(
        tmp_path, monkeypatch
    )

    data = payload(worker["agent_id"])
    data["kind"] = "email:send"

    response = oak.post(
        "/api/customer/jobs",
        json=data,
    )

    assert response.status_code == 422
