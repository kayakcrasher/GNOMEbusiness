from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.security import create_key

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "tenant_guard.db"),
    )
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    initialize()

    with connect() as db:
        first = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Oak",),
        ).lastrowid

        second = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Pine",),
        ).lastrowid

        lead = db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, ?)
            """,
            (second, "Pine Prospect"),
        ).lastrowid

    return first, second, lead, create_key(first)


def test_missing_key_rejected(tmp_path, monkeypatch):
    first, _, _, _ = seed(tmp_path, monkeypatch)

    response = client.get(
        f"/api/businesses/{first}/leads"
    )

    assert response.status_code == 401


def test_own_business_allowed(tmp_path, monkeypatch):
    first, _, _, key = seed(tmp_path, monkeypatch)

    response = client.get(
        f"/api/businesses/{first}/leads",
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200


def test_other_business_denied(tmp_path, monkeypatch):
    _, second, _, key = seed(tmp_path, monkeypatch)

    response = client.get(
        f"/api/businesses/{second}/leads",
        headers={"X-API-Key": key},
    )

    assert response.status_code == 403


def test_other_business_record_denied(
    tmp_path, monkeypatch
):
    _, _, lead_id, key = seed(tmp_path, monkeypatch)

    response = client.patch(
        f"/api/leads/{lead_id}",
        headers={"X-API-Key": key},
        json={"status": "interested"},
    )

    assert response.status_code == 403


def test_cross_business_creation_denied(
    tmp_path, monkeypatch
):
    _, second, _, key = seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/leads",
        headers={"X-API-Key": key},
        json={
            "business_id": second,
            "company": "Unauthorized Prospect",
        },
    )

    assert response.status_code == 403
