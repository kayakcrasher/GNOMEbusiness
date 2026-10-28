from fastapi.testclient import TestClient

from app.main import app
from app.database import connect
from app.reporting import business_report

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "reports.db"),
    )

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                company TEXT NOT NULL,
                contact TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'new'
            )
        """)

        business = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Reporting Test",),
        )
        business_id = business.lastrowid

        lead = db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, ?)
            """,
            (business_id, "Oak Company"),
        )
        lead_id = lead.lastrowid

    return business_id, lead_id


def test_empty_activity(tmp_path, monkeypatch):
    business_id, _ = seed(tmp_path, monkeypatch)

    response = client.get(
        f"/api/businesses/{business_id}/report"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_leads"] == 1
    assert data["conversion_rate"] == 0


def test_report_counts_booking(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY,
                business_id INTEGER,
                lead_id INTEGER,
                title TEXT,
                starts_at TEXT,
                notes TEXT DEFAULT '',
                status TEXT DEFAULT 'scheduled'
            )
        """)

        db.execute(
            """
            INSERT INTO appointments
            (business_id, lead_id, title, starts_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                business_id,
                lead_id,
                "Discovery Call",
                "2026-11-15T14:00:00+00:00",
            ),
        )

    response = client.get(
        f"/api/businesses/{business_id}/report"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["booked_leads"] == 1
    assert data["conversion_rate"] == 100.0


def test_missing_business(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.get(
        "/api/businesses/999/report"
    )

    assert response.status_code == 404


def test_reports_script_served():
    response = client.get("/static/js/reports.js")
    assert response.status_code == 200


def test_reporting_route_registered(tmp_path, monkeypatch):
    business_id, _ = seed(tmp_path, monkeypatch)

    response = client.get(
        f"/api/businesses/{business_id}/report"
    )

    assert response.status_code == 200
    assert "conversion_rate" in response.json()
