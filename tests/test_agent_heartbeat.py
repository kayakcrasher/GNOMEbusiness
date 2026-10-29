from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.auth import create_user
from app.agent_gateway import provision_agent
from app.agent_operations import connection_status

client = TestClient(
    app, base_url="https://testserver"
)


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "heartbeat.db"),
    )
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")
    initialize()

    with connect() as db:
        business = db.execute(
            "INSERT INTO businesses(name) VALUES ('Oak')"
        ).lastrowid

    create_user(
        business, "heartbeat-owner", "secure-password-123"
    )

    worker = provision_agent(
        business, "Worker", ["jobs:work"]
    )

    assert client.post(
        "/api/auth/login",
        json={
            "username": "heartbeat-owner",
            "password": "secure-password-123",
        },
    ).status_code == 200

    return worker


def test_heartbeat_requires_token(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    guest = TestClient(app)

    assert guest.post(
        "/api/agents/heartbeat"
    ).status_code == 401


def test_heartbeat_updates_connection(tmp_path, monkeypatch):
    worker = setup(tmp_path, monkeypatch)

    response = client.post(
        "/api/agents/heartbeat",
        headers={
            "Authorization": "Bearer " + worker["token"]
        },
    )

    assert response.status_code == 200

    operations = client.get(
        "/api/customer/operations"
    ).json()

    assert operations["agents"][0][
        "connection_status"
    ] == "online"


def test_never_connected(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    operations = client.get(
        "/api/customer/operations"
    ).json()

    assert operations["agents"][0][
        "connection_status"
    ] == "never_connected"


def test_stale_heartbeat_offline():
    old = (
        datetime.now(timezone.utc)
        - timedelta(minutes=5)
    ).isoformat()

    assert connection_status(old) == "offline"


def test_recent_heartbeat_online():
    recent = datetime.now(timezone.utc).isoformat()

    assert connection_status(recent) == "online"
