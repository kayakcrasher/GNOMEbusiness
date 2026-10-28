from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ROOT = Path(__file__).resolve().parent.parent


def test_lead_form_served():
    response = client.get(
        "/static/js/lead-form.js"
    )
    assert response.status_code == 200
    assert "Add Lead" in response.text


def test_form_connected():
    html = (ROOT / "frontend/index.html").read_text()
    assert 'src="/static/js/lead-form.js"' in html


def test_form_uses_api():
    js = (ROOT / "frontend/js/lead-form.js").read_text()
    assert 'fetch("/api/leads"' in js


def test_form_has_required_company():
    js = (ROOT / "frontend/js/lead-form.js").read_text()
    assert 'name="company" required' in js
