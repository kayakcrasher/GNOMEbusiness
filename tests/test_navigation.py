from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ROOT = Path(__file__).resolve().parent.parent


def navigation_source():
    return (
        ROOT / "frontend/js/navigation.js"
    ).read_text()


def test_navigation_served():
    response = client.get("/static/js/navigation.js")
    assert response.status_code == 200


def test_navigation_loaded():
    html = (
        ROOT / "frontend/index.html"
    ).read_text()

    assert '/static/js/navigation.js' in html


def test_overview_connected():
    js = navigation_source()

    assert "dashboard:" in js
    assert "navigate(view)" in js
    assert "window.scrollTo" in js


def test_leads_connected():
    js = navigation_source()

    assert "leads:" in js
    assert 'document.querySelector("#leads")' in js


def test_appointments_connected():
    js = navigation_source()

    assert "appointments:" in js
    assert 'document.querySelector("#appointments")' in js
