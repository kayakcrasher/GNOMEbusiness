from fastapi.testclient import TestClient

from app.main import app
from app.database import connect
from app.followups import migrate

client = TestClient(app)


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "followups.db"),
    )
    migrate()

    with connect() as db:
        business = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Test Company",),
        )
        lead = db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, ?)
            """,
            (business.lastrowid, "Oakridge"),
        )

    return business.lastrowid, lead.lastrowid


def test_migration(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    with connect() as db:
        columns = {
            row["name"]
            for row in db.execute(
                "PRAGMA table_info(leads)"
            )
        }

    assert "follow_up" in columns
    assert "notes" in columns


def test_update_followup(tmp_path, monkeypatch):
    _, lead_id = setup(tmp_path, monkeypatch)

    response = client.patch(
        f"/api/leads/{lead_id}/followup",
        json={
            "follow_up": "2026-11-15",
            "notes": "Call purchasing manager",
        },
    )

    assert response.status_code == 200
    assert response.json()["notes"] == "Call purchasing manager"


def test_list_followups(tmp_path, monkeypatch):
    business_id, lead_id = setup(tmp_path, monkeypatch)

    client.patch(
        f"/api/leads/{lead_id}/followup",
        json={
            "follow_up": "2026-11-15",
            "notes": "Send proposal",
        },
    )

    response = client.get(
        f"/api/businesses/{business_id}/followups"
    )

    assert response.status_code == 200
    assert len(response.json()["followups"]) == 1


def test_missing_lead(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    response = client.patch(
        "/api/leads/999/followup",
        json={"notes": "Nothing"},
    )

    assert response.status_code == 404


def test_closed_leads_excluded(tmp_path, monkeypatch):
    business_id, lead_id = setup(tmp_path, monkeypatch)

    client.patch(
        f"/api/leads/{lead_id}/followup",
        json={"follow_up": "2026-11-15"},
    )

    client.patch(
        f"/api/leads/{lead_id}",
        json={"status": "closed"},
    )

    response = client.get(
        f"/api/businesses/{business_id}/followups"
    )

    assert response.json()["followups"] == []
