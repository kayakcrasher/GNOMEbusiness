from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "dashboard.db"),
    )


def create_business(name="Test Company"):
    response = client.post(
        "/api/businesses",
        json={"name": name},
    )
    return response.json()["id"]


def test_create_business(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/businesses",
        json={"name": "Oakridge Supply"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Oakridge Supply"


def test_empty_dashboard(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)

    business_id = create_business()

    response = client.get(
        f"/api/businesses/{business_id}/dashboard"
    )

    assert response.status_code == 200
    assert response.json()["total_leads"] == 0


def test_dashboard_counts(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)

    business_id = create_business()

    client.post(
        "/api/leads",
        json={
            "business_id": business_id,
            "company": "Pine Valley",
        },
    )

    response = client.get(
        f"/api/businesses/{business_id}/dashboard"
    )

    data = response.json()

    assert data["total_leads"] == 1
    assert data["pipeline"]["new"] == 1


def test_recent_leads(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)

    business_id = create_business()

    client.post(
        "/api/leads",
        json={
            "business_id": business_id,
            "company": "Summit Works",
        },
    )

    response = client.get(
        f"/api/businesses/{business_id}/dashboard"
    )

    assert response.json()["recent_leads"][0][
        "company"
    ] == "Summit Works"


def test_missing_business(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)

    response = client.get(
        "/api/businesses/999/dashboard"
    )

    assert response.status_code == 404


def test_business_isolation(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)

    first = create_business("Company One")
    second = create_business("Company Two")

    client.post(
        "/api/leads",
        json={
            "business_id": first,
            "company": "Private Lead",
        },
    )

    response = client.get(
        f"/api/businesses/{second}/dashboard"
    )

    assert response.json()["total_leads"] == 0
    assert response.json()["recent_leads"] == []
