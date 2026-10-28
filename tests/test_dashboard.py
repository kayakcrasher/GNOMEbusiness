from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "GNOMEbusiness" in response.text

def test_stylesheet():
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert "--gold" in response.text

def test_javascript():
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert "pipeline" in response.text
