from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.agent_gateway import provision_agent

client = TestClient(app)


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "workstation.db"),
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

    a = provision_agent(
        oak, "Leadkeeper", ["jobs:work"]
    )
    b = provision_agent(
        oak, "Researcher", ["jobs:work"]
    )
    other = provision_agent(
        pine, "Pine Agent", ["jobs:work"]
    )

    return a, b, other


def auth(agent):
    return {
        "Authorization": "Bearer " + agent["token"]
    }


def create(agent):
    return client.post(
        "/api/workstation/jobs",
        headers=auth(agent),
        json={
            "kind": "lead:analyze",
            "instructions": {"lead_id": 12},
        },
    )


def test_create_job(tmp_path, monkeypatch):
    a, _, _ = setup(tmp_path, monkeypatch)

    response = create(a)

    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_claim_job(tmp_path, monkeypatch):
    a, b, _ = setup(tmp_path, monkeypatch)
    job_id = create(a).json()["id"]

    response = client.post(
        f"/api/workstation/jobs/{job_id}/claim",
        headers=auth(b),
    )

    assert response.status_code == 409


def test_double_claim_blocked(tmp_path, monkeypatch):
    a, b, _ = setup(tmp_path, monkeypatch)
    job_id = create(a).json()["id"]

    first = client.post(
        f"/api/workstation/jobs/{job_id}/claim",
        headers=auth(a),
    )

    second = client.post(
        f"/api/workstation/jobs/{job_id}/claim",
        headers=auth(b),
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_tenant_isolation(tmp_path, monkeypatch):
    a, _, other = setup(tmp_path, monkeypatch)
    job_id = create(a).json()["id"]

    response = client.post(
        f"/api/workstation/jobs/{job_id}/claim",
        headers=auth(other),
    )

    assert response.status_code == 409

    listing = client.get(
        "/api/workstation/jobs",
        headers=auth(other),
    )

    assert listing.json()["jobs"] == []


def test_only_owner_completes(tmp_path, monkeypatch):
    a, b, _ = setup(tmp_path, monkeypatch)
    job_id = create(a).json()["id"]

    client.post(
        f"/api/workstation/jobs/{job_id}/claim",
        headers=auth(a),
    )

    url = f"/api/workstation/jobs/{job_id}/complete"

    denied = client.post(
        url,
        headers=auth(b),
        json={"result": {"score": 80}},
    )

    allowed = client.post(
        url,
        headers=auth(a),
        json={"result": {"score": 80}},
    )

    assert denied.status_code == 409
    assert allowed.status_code == 200



def test_worker_only_sees_assigned_jobs(
    tmp_path, monkeypatch
):
    a, b, _ = setup(tmp_path, monkeypatch)

    created = create(a)
    assert created.status_code == 201

    own = client.get(
        "/api/workstation/jobs",
        headers=auth(a),
    )
    other = client.get(
        "/api/workstation/jobs",
        headers=auth(b),
    )

    assert len(own.json()["jobs"]) == 1
    assert other.json()["jobs"] == []
