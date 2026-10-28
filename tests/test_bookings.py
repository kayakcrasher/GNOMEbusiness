from fastapi.testclient import TestClient

from app.main import app
from app.database import connect
from app.appointments.api import migrate

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "bookings.db"),
    )
    migrate()

    with connect() as db:
        cursor = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("GNOME Test",),
        )
        return cursor.lastrowid


def test_create_booking(tmp_path, monkeypatch):
    business_id = seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/appointments",
        json={
            "business_id": business_id,
            "title": "Client meeting",
            "starts_at": "2026-11-15T14:00:00Z",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "scheduled"


def test_list_bookings(tmp_path, monkeypatch):
    business_id = seed(tmp_path, monkeypatch)

    client.post(
        "/api/appointments",
        json={
            "business_id": business_id,
            "title": "Demo",
            "starts_at": "2026-11-15T14:00:00Z",
        },
    )

    response = client.get(
        f"/api/businesses/{business_id}/appointments"
    )

    assert response.status_code == 200
    assert len(response.json()["appointments"]) == 1


def test_complete_booking(tmp_path, monkeypatch):
    business_id = seed(tmp_path, monkeypatch)

    booking = client.post(
        "/api/appointments",
        json={
            "business_id": business_id,
            "title": "Demo",
            "starts_at": "2026-11-15T14:00:00Z",
        },
    ).json()

    response = client.patch(
        f"/api/appointments/{booking['id']}",
        json={"status": "completed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_missing_business(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/appointments",
        json={
            "business_id": 999,
            "title": "Invalid",
            "starts_at": "2026-11-15T14:00:00Z",
        },
    )

    assert response.status_code == 404


def test_booking_requires_timezone(tmp_path, monkeypatch):
    business_id = seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/appointments",
        json={
            "business_id": business_id,
            "title": "Invalid time",
            "starts_at": "2026-11-15T14:00:00",
        },
    )

    assert response.status_code == 422
