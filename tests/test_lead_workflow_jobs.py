from tests.test_agent_workstation import setup, auth, client


def test_lead_workflow_can_be_queued(tmp_path, monkeypatch):
    agent, _, _ = setup(tmp_path, monkeypatch)

    response = client.post(
        "/api/workstation/jobs",
        headers=auth(agent),
        json={
            "kind": "lead:process",
            "instructions": {
                "message": "Need an urgent quote"
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_unsafe_job_kind_rejected(tmp_path, monkeypatch):
    agent, _, _ = setup(tmp_path, monkeypatch)

    response = client.post(
        "/api/workstation/jobs",
        headers=auth(agent),
        json={
            "kind": "system:delete",
            "instructions": {},
        },
    )

    assert response.status_code == 422
