from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.auth import create_user

client = TestClient(app)


def setup_users(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "connectors.db"),
    )
    monkeypatch.setenv(
        "GNOME_ENFORCE_AUTH",
        "1",
    )

    initialize()

    with connect() as db:
        oak = db.execute(
            "INSERT INTO businesses(name) VALUES ('Oak')"
        ).lastrowid
        pine = db.execute(
            "INSERT INTO businesses(name) VALUES ('Pine')"
        ).lastrowid

    create_user(oak, "oak-owner", "secure-password-123")
    create_user(pine, "pine-owner", "secure-password-456")

    oak_client = TestClient(
        app,
        base_url="https://testserver",
    )
    pine_client = TestClient(
        app,
        base_url="https://testserver",
    )

    assert oak_client.post(
        "/api/auth/login",
        json={
            "username": "oak-owner",
            "password": "secure-password-123",
        },
    ).status_code == 200

    assert pine_client.post(
        "/api/auth/login",
        json={
            "username": "pine-owner",
            "password": "secure-password-456",
        },
    ).status_code == 200

    return oak_client, pine_client


def test_login_required(tmp_path, monkeypatch):
    setup_users(tmp_path, monkeypatch)

    assert client.get(
        "/api/connectors/manage"
    ).status_code == 401


def test_customer_creates_connector(
    tmp_path, monkeypatch
):
    oak, _ = setup_users(tmp_path, monkeypatch)

    response = oak.post(
        "/api/connectors/manage",
        json={
            "name": "Muse",
            "scopes": ["leads:read"],
        },
    )

    assert response.status_code == 201
    assert response.json()["token"].startswith("gna_")

    listing = oak.get(
        "/api/connectors/manage"
    ).json()

    assert len(listing["connectors"]) == 1
    assert "token" not in listing["connectors"][0]


def test_customer_cannot_access_other_tenant(
    tmp_path, monkeypatch
):
    oak, pine = setup_users(tmp_path, monkeypatch)

    created = oak.post(
        "/api/connectors/manage",
        json={
            "name": "Muse",
            "scopes": ["leads:read"],
        },
    ).json()

    denied = pine.post(
        f"/api/connectors/manage/{created['id']}/revoke"
    )

    assert denied.status_code == 404


def test_customer_can_revoke_connector(
    tmp_path, monkeypatch
):
    oak, _ = setup_users(tmp_path, monkeypatch)

    created = oak.post(
        "/api/connectors/manage",
        json={
            "name": "Muse",
            "scopes": ["leads:read"],
        },
    ).json()

    response = oak.post(
        f"/api/connectors/manage/{created['id']}/revoke"
    )

    assert response.status_code == 200

    rejected = client.get(
        "/api/agents/leads",
        headers={
            "Authorization": (
                "Bearer " + created["token"]
            )
        },
    )

    assert rejected.status_code == 401


def test_rejects_excessive_permissions(
    tmp_path, monkeypatch
):
    oak, _ = setup_users(tmp_path, monkeypatch)

    response = oak.post(
        "/api/connectors/manage",
        json={
            "name": "Muse",
            "scopes": ["proposals:create"],
        },
    )

    assert response.status_code == 422
