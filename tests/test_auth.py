from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.auth import (
    create_user,
    hash_password,
    verify_password,
)

client = TestClient(
    app,
    base_url="https://testserver",
)


def seed(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "auth.db"),
    )

    initialize()

    with connect() as db:
        business_id = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Oak Company",),
        ).lastrowid

    create_user(
        business_id,
        "oak_admin",
        "StrongPassword123!",
    )

    return business_id


def test_password_hashing():
    stored = hash_password("StrongPassword123!")

    assert stored != "StrongPassword123!"
    assert verify_password("StrongPassword123!", stored)
    assert not verify_password("WrongPassword123!", stored)


def test_login_success(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={
            "username": "oak_admin",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert "httponly" in response.headers[
        "set-cookie"
    ].lower()


def test_wrong_password(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={
            "username": "oak_admin",
            "password": "wrong",
        },
    )

    assert response.status_code == 401


def test_session_identity(tmp_path, monkeypatch):
    business_id = seed(tmp_path, monkeypatch)

    with TestClient(
        app,
        base_url="https://testserver",
    ) as browser:
        browser.post(
            "/api/auth/login",
            json={
                "username": "oak_admin",
                "password": "StrongPassword123!",
            },
        )

        response = browser.get("/api/auth/me")

        assert response.status_code == 200
        assert response.json()["business_id"] == business_id


def test_logout_revokes_session(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)

    with TestClient(
        app,
        base_url="https://testserver",
    ) as browser:
        browser.post(
            "/api/auth/login",
            json={
                "username": "oak_admin",
                "password": "StrongPassword123!",
            },
        )

        logout = browser.post("/api/auth/logout")
        assert logout.status_code == 200

        response = browser.get("/api/auth/me")
        assert response.status_code == 401
