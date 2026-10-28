from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.agent_gateway import provision_agent, revoke_agent

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "agents.db"),
    )
    monkeypatch.delenv("GNOME_ENFORCE_AUTH", raising=False)

    initialize()

    with connect() as db:
        first = db.execute(
            "INSERT INTO businesses(name) VALUES ('Oak')"
        ).lastrowid

        second = db.execute(
            "INSERT INTO businesses(name) VALUES ('Pine')"
        ).lastrowid

        db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, 'Oak Prospect')
            """,
            (first,),
        )

        db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, 'Pine Prospect')
            """,
            (second,),
        )

    credential = provision_agent(
        first,
        "Leadkeeper",
        ["leads:read"],
    )

    return first, credential


def headers(credential):
    return {
        "Authorization": "Bearer " + credential["token"]
    }


def test_missing_token(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.get("/api/agents/leads")
    assert response.status_code == 401


def test_agent_identity(tmp_path, monkeypatch):
    business_id, credential = seed(tmp_path, monkeypatch)

    response = client.get(
        "/api/agents/me",
        headers=headers(credential),
    )

    assert response.status_code == 200
    assert response.json()["business_id"] == business_id


def test_tenant_isolation(tmp_path, monkeypatch):
    _, credential = seed(tmp_path, monkeypatch)

    response = client.get(
        "/api/agents/leads",
        headers=headers(credential),
    )

    assert response.status_code == 200

    companies = [
        lead["company"]
        for lead in response.json()["leads"]
    ]

    assert companies == ["Oak Prospect"]


def test_scope_denied(tmp_path, monkeypatch):
    _, credential = seed(tmp_path, monkeypatch)

    response = client.get(
        "/api/agents/appointments",
        headers=headers(credential),
    )

    assert response.status_code == 403


def test_revoked_agent(tmp_path, monkeypatch):
    _, credential = seed(tmp_path, monkeypatch)

    assert revoke_agent(credential["agent_id"])

    response = client.get(
        "/api/agents/leads",
        headers=headers(credential),
    )

    assert response.status_code == 401
