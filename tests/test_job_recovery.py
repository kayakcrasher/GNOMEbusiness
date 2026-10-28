from fastapi.testclient import TestClient

from app.main import app
from app.database import connect
from tests.test_agent_workstation import (
    setup,
    auth,
    create,
)

client = TestClient(app)


def claim(agent, job_id):
    return client.post(
        f"/api/workstation/jobs/{job_id}/claim",
        headers=auth(agent),
    )


def recover(agent, job_id):
    return client.post(
        f"/api/workstation/jobs/{job_id}/recover",
        headers=auth(agent),
    )


def make_stale(job_id):
    with connect() as db:
        db.execute(
            """
            UPDATE agent_jobs
            SET claimed_at = datetime(
                'now', '-20 minutes'
            )
            WHERE id = ?
            """,
            (job_id,),
        )


def test_owner_recovers_stale_job(tmp_path, monkeypatch):
    owner, _, _ = setup(tmp_path, monkeypatch)
    job_id = create(owner).json()["id"]

    assert claim(owner, job_id).status_code == 200

    make_stale(job_id)

    result = recover(owner, job_id)

    assert result.status_code == 200
    assert result.json()["recovered"] is True
    assert result.json()["status"] == "working"


def test_fresh_job_cannot_be_recovered(
    tmp_path, monkeypatch
):
    owner, _, _ = setup(tmp_path, monkeypatch)
    job_id = create(owner).json()["id"]

    claim(owner, job_id)

    assert recover(owner, job_id).status_code == 409


def test_other_agent_cannot_recover(
    tmp_path, monkeypatch
):
    owner, other, _ = setup(tmp_path, monkeypatch)
    job_id = create(owner).json()["id"]

    claim(owner, job_id)
    make_stale(job_id)

    assert recover(other, job_id).status_code == 409


def test_other_business_cannot_recover(
    tmp_path, monkeypatch
):
    owner, _, outsider = setup(
        tmp_path, monkeypatch
    )
    job_id = create(owner).json()["id"]

    claim(owner, job_id)
    make_stale(job_id)

    assert recover(outsider, job_id).status_code == 409


def test_completed_job_cannot_recover(
    tmp_path, monkeypatch
):
    owner, _, _ = setup(tmp_path, monkeypatch)
    job_id = create(owner).json()["id"]

    claim(owner, job_id)
    make_stale(job_id)

    completed = client.post(
        f"/api/workstation/jobs/{job_id}/complete",
        headers=auth(owner),
        json={"result": {"ok": True}},
    )

    assert completed.status_code == 200
    assert recover(owner, job_id).status_code == 409
