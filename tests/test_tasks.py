from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.database import connect
from app.followups import migrate
from app.main import app

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "tasks.db"),
    )
    migrate()

    with connect() as db:
        business = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Task Test",),
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


def test_empty_tasks(tmp_path, monkeypatch):
    business_id, _ = seed(tmp_path, monkeypatch)

    response = client.get(
        f"/api/businesses/{business_id}/tasks"
    )

    assert response.status_code == 200
    assert response.json()["summary"]["today"] == 0


def test_today_task(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    client.patch(
        f"/api/leads/{lead_id}/followup",
        json={"follow_up": date.today().isoformat()},
    )

    response = client.get(
        f"/api/businesses/{business_id}/tasks"
    )

    assert response.json()["summary"]["today"] == 1


def test_overdue_task(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    yesterday = (
        date.today() - timedelta(days=1)
    ).isoformat()

    client.patch(
        f"/api/leads/{lead_id}/followup",
        json={"follow_up": yesterday},
    )

    response = client.get(
        f"/api/businesses/{business_id}/tasks"
    )

    assert response.json()["summary"]["overdue"] == 1


def test_complete_task(tmp_path, monkeypatch):
    business_id, lead_id = seed(tmp_path, monkeypatch)

    client.patch(
        f"/api/leads/{lead_id}/followup",
        json={"follow_up": date.today().isoformat()},
    )

    response = client.patch(
        f"/api/leads/{lead_id}/complete-followup"
    )

    assert response.status_code == 200
    assert response.json()["completed"] is True

    tasks = client.get(
        f"/api/businesses/{business_id}/tasks"
    )

    assert tasks.json()["tasks"] == []


def test_missing_business(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.get(
        "/api/businesses/999/tasks"
    )

    assert response.status_code == 404


def test_missing_lead(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.patch(
        "/api/leads/999/complete-followup"
    )

    assert response.status_code == 404
