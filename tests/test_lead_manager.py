from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parent.parent


def test_manager_served():
    response = client.get(
        "/static/js/lead-manager.js"
    )
    assert response.status_code == 200


def test_manager_connected():
    html = (ROOT / "frontend/index.html").read_text()
    assert 'src="/static/js/lead-manager.js"' in html


def test_manager_updates_api():
    js = (ROOT / "frontend/js/lead-manager.js").read_text()
    assert 'method: "PATCH"' in js


def test_lead_rows_have_ids():
    js = (ROOT / "frontend/js/live.js").read_text()
    assert "row.dataset.leadId" in js
