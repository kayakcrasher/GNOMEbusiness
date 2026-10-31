"""Authenticated cross-tenant security regression tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import connect, initialize
from app.security import create_key
from app.approvals import migrate as approvals_migrate


@pytest.fixture
def tenants(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "tenants.db"),
    )
    monkeypatch.setenv("GNOME_ENV", "production")
    monkeypatch.setenv("GNOME_ENFORCE_AUTH", "1")

    initialize()

    with connect() as db:
        oak = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Oak Company",),
        ).lastrowid

        pine = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Pine Company",),
        ).lastrowid

        lead = db.execute(
            """
            INSERT INTO leads(business_id, company)
            VALUES (?, ?)
            """,
            (oak, "Private Oak Prospect"),
        ).lastrowid

    return {
        "client": TestClient(app),
        "oak": oak,
        "pine": pine,
        "lead": lead,
        "oak_headers": {
            "X-API-Key": create_key(oak)
        },
        "pine_headers": {
            "X-API-Key": create_key(pine)
        },
    }


def test_owner_can_read_own_leads(tenants):
    t = tenants

    response = t["client"].get(
        f'/api/businesses/{t["oak"]}/leads',
        headers=t["oak_headers"],
    )

    assert response.status_code == 200
    assert "Private Oak Prospect" in response.text


def test_other_tenant_cannot_read_leads(tenants):
    t = tenants

    response = t["client"].get(
        f'/api/businesses/{t["oak"]}/leads',
        headers=t["pine_headers"],
    )

    assert response.status_code == 403
    assert "Private Oak Prospect" not in response.text


def test_other_tenant_cannot_update_lead(tenants):
    t = tenants

    response = t["client"].patch(
        f'/api/leads/{t["lead"]}',
        headers=t["pine_headers"],
        json={"status": "closed"},
    )

    assert response.status_code == 403

    with connect() as db:
        row = db.execute(
            "SELECT status FROM leads WHERE id = ?",
            (t["lead"],),
        ).fetchone()

    assert row["status"] == "new"


def test_other_tenant_cannot_create_lead(tenants):
    t = tenants

    response = t["client"].post(
        "/api/leads",
        headers=t["pine_headers"],
        json={
            "business_id": t["oak"],
            "company": "Injected Prospect",
        },
    )

    assert response.status_code == 403


def test_tenant_can_create_own_lead(tenants):
    t = tenants

    response = t["client"].post(
        "/api/leads",
        headers=t["oak_headers"],
        json={
            "business_id": t["oak"],
            "company": "Authorized Prospect",
        },
    )

    assert response.status_code == 201


def test_other_tenant_cannot_read_report(tenants):
    t = tenants

    response = t["client"].get(
        f'/api/businesses/{t["oak"]}/report',
        headers=t["pine_headers"],
    )

    assert response.status_code == 403


def test_owner_approval_inbox_isolated(tenants):
    t = tenants
    approvals_migrate()

    response = t["client"].get(
        "/api/approvals",
        headers=t["oak_headers"],
    )

    assert response.status_code == 200
    assert response.json()["proposals"] == []


def test_invalid_key_rejected(tenants):
    t = tenants

    response = t["client"].get(
        f'/api/businesses/{t["oak"]}/leads',
        headers={"X-API-Key": "gnb_invalid"},
    )

    assert response.status_code == 401


def test_missing_key_rejected(tenants):
    t = tenants

    response = t["client"].get(
        f'/api/businesses/{t["oak"]}/leads'
    )

    assert response.status_code == 401
