from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_agent_page_loads():
    response = client.get("/agents")
    assert response.status_code == 200


def test_agent_page_has_review_controls():
    response = client.get("/agents")
    assert 'id="proposals"' in response.text
    assert 'id="connect"' in response.text
    assert 'id="disconnect"' in response.text


def test_agent_page_uses_approval_api():
    response = client.get("/agents")
    assert "/api/approvals" in response.text
    assert "X-API-Key" in response.text
