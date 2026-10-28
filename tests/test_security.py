from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.security import create_key, hash_key, migrate

client = TestClient(app)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "security.db"),
    )

    initialize()

    with connect() as db:
        first = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Oak Company",),
        ).lastrowid

        second = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Pine Company",),
        ).lastrowid

        db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, ?)
            """,
            (first, "Oak Prospect"),
        )

    return first, second


def test_missing_key_rejected(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.get("/api/secure/report")
    assert response.status_code == 401


def test_invalid_key_rejected(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.get(
        "/api/secure/report",
        headers={"X-API-Key": "gnb_invalid"},
    )

    assert response.status_code == 401


def test_valid_key_returns_own_report(tmp_path, monkeypatch):
    first, _ = seed(tmp_path, monkeypatch)
    key = create_key(first)

    response = client.get(
        "/api/secure/report",
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200
    assert response.json()["business"]["id"] == first
    assert response.json()["total_leads"] == 1


def test_business_isolation(tmp_path, monkeypatch):
    first, second = seed(tmp_path, monkeypatch)

    key = create_key(second)

    response = client.get(
        "/api/secure/report",
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200
    assert response.json()["business"]["id"] == second
    assert response.json()["total_leads"] == 0


def test_key_stored_as_hash(tmp_path, monkeypatch):
    first, _ = seed(tmp_path, monkeypatch)
    key = create_key(first)

    with connect() as db:
        row = db.execute(
            "SELECT key_hash FROM api_keys"
        ).fetchone()

    assert row["key_hash"] == hash_key(key)
    assert key != row["key_hash"]
