from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "operational"

def test_platform():
    r = client.get("/api/health")
    assert r.json()["platform"] == "GNOMEbusiness"

def test_modules():
    r = client.get("/api/modules")
    assert len(r.json()["modules"]) == 3
