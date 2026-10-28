from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize

client = TestClient(app)


def setup_business(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "leads.db")
    )

    initialize()

    with connect() as db:
        db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Test Business",)
        )


def test_create_lead(tmp_path, monkeypatch):
    setup_business(tmp_path, monkeypatch)

    response = client.post(
        "/api/leads",
        json={
            "business_id": 1,
            "company": "Oakridge Supply",
            "contact": "Alex",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "new"


def test_list_leads(tmp_path, monkeypatch):
    setup_business(tmp_path, monkeypatch)

    client.post(
        "/api/leads",
        json={
            "business_id": 1,
            "company": "Pine Valley",
        },
    )

    response = client.get("/api/businesses/1/leads")

    assert response.status_code == 200
    assert len(response.json()["leads"]) == 1


def test_update_lead(tmp_path, monkeypatch):
    setup_business(tmp_path, monkeypatch)

    created = client.post(
        "/api/leads",
        json={
            "business_id": 1,
            "company": "Summit Works",
        },
    ).json()

    lead_id = created["id"]

    response = client.patch(
        f"/api/leads/{lead_id}",
        json={"status": "interested"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "interested"


def test_missing_business(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "missing.db")
    )

    response = client.post(
        "/api/leads",
        json={
            "business_id": 999,
            "company": "Unknown",
        },
    )

    assert response.status_code == 404


def test_invalid_status(tmp_path, monkeypatch):
    setup_business(tmp_path, monkeypatch)

    response = client.patch(
        "/api/leads/1",
        json={"status": "banana"},
    )

    assert response.status_code == 422
