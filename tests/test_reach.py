from fastapi.testclient import TestClient

from app.main import app
from app.database import connect
from app.outreach.api import migrate

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "reach.db"),
    )
    migrate()

    with connect() as db:
        business = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("GNOME Test",),
        )
        business_id = business.lastrowid

        lead = db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, ?)
            """,
            (business_id, "Oak Company"),
        )

        return business_id, lead.lastrowid


def test_create_draft(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/outreach",
        json={
            "business_id": business_id,
            "lead_id": lead_id,
            "subject": "Hello Oak",
            "body": "Would you be open to a conversation?",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "draft"


def test_list_drafts(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    client.post(
        "/api/outreach",
        json={
            "business_id": business_id,
            "lead_id": lead_id,
            "subject": "Introduction",
            "body": "Hello there",
        },
    )

    response = client.get(
        f"/api/businesses/{business_id}/outreach"
    )

    assert response.status_code == 200
    assert len(response.json()["messages"]) == 1


def test_mark_ready(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    message = client.post(
        "/api/outreach",
        json={
            "business_id": business_id,
            "lead_id": lead_id,
            "subject": "Hello",
            "body": "Let's connect",
        },
    ).json()

    response = client.patch(
        f"/api/outreach/{message['id']}",
        json={"status": "ready"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_reject_other_business_lead(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    with connect() as db:
        other = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Other Business",),
        )
        other_id = other.lastrowid

    response = client.post(
        "/api/outreach",
        json={
            "business_id": other_id,
            "lead_id": lead_id,
            "subject": "Invalid",
            "body": "Wrong business",
        },
    )

    assert response.status_code == 404


def test_missing_message(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.patch(
        "/api/outreach/999",
        json={"status": "sent"},
    )

    assert response.status_code == 404
