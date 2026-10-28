from fastapi.testclient import TestClient

from app.main import app
from app.database import connect
from app.appointments.conversion import migrate

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "conversions.db"),
    )
    migrate()

    with connect() as db:
        business = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Test Business",),
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


def payload(business_id, lead_id):
    return {
        "business_id": business_id,
        "lead_id": lead_id,
        "title": "Discovery Call",
        "starts_at": "2026-11-15T14:00:00Z",
    }


def test_book_lead(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/conversions/book",
        json=payload(business_id, lead_id),
    )

    assert response.status_code == 201
    assert response.json()["lead_status"] == "booked"

    with connect() as db:
        lead = db.execute(
            "SELECT status FROM leads WHERE id = ?",
            (lead_id,),
        ).fetchone()

        appointment = db.execute(
            "SELECT lead_id FROM appointments"
        ).fetchone()

    assert lead["status"] == "booked"
    assert appointment["lead_id"] == lead_id


def test_reject_wrong_business(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/conversions/book",
        json=payload(business_id + 1, lead_id),
    )

    assert response.status_code == 404


def test_reject_naive_datetime(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    data = payload(business_id, lead_id)
    data["starts_at"] = "2026-11-15T14:00:00"

    response = client.post(
        "/api/conversions/book",
        json=data,
    )

    assert response.status_code == 422


def test_reject_closed_lead(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    with connect() as db:
        db.execute(
            "UPDATE leads SET status = 'closed' WHERE id = ?",
            (lead_id,),
        )

    response = client.post(
        "/api/conversions/book",
        json=payload(business_id, lead_id),
    )

    assert response.status_code == 409


def test_conversion_ui_served():
    response = client.get("/static/js/conversions.js")
    assert response.status_code == 200
