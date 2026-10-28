from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_page_exists():
    response = client.get("/login")
    assert response.status_code == 200


def test_login_page_has_form():
    response = client.get("/login")
    assert 'id="login-form"' in response.text


def test_login_page_has_password_field():
    response = client.get("/login")
    assert 'type="password"' in response.text


def test_login_stylesheet_served():
    response = client.get("/static/css/login.css")
    assert response.status_code == 200
    assert ".login-card" in response.text


def test_login_script_served():
    response = client.get("/static/js/login.js")
    assert response.status_code == 200
    assert "/api/auth/login" in response.text
