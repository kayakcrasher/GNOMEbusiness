from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_muse_manifest_available():
    response = client.get("/api/connectors/muse")

    assert response.status_code == 200

    data = response.json()

    assert data["provider"] == "muse"
    assert data["authentication"]["type"] == "bearer"


def test_connector_exposes_supported_jobs():
    data = client.get(
        "/api/connectors/muse"
    ).json()

    capabilities = {
        item["name"]: item
        for item in data["capabilities"]
    }

    create = capabilities["create_job"]

    assert create["path"] == "/api/workstation/jobs"
    assert create["scope"] == "jobs:work"
    assert "lead:process" in create["allowed_kinds"]


def test_connector_does_not_expose_secrets():
    response = client.get("/api/connectors/muse")

    text = response.text.lower()

    assert "gna_" not in text
    assert "api_key" not in text
    assert "token_hash" not in text
    assert "password" not in text


def test_connector_does_not_enable_execution():
    data = client.get(
        "/api/connectors/muse"
    ).json()

    assert data["safety"][
        "external_actions_enabled"
    ] is False
