import pytest
from fastapi import HTTPException

from app.database import connect
from app.admin_security import (
    ADMIN_PERMISSIONS,
    bootstrap_admin,
    authorize_admin,
)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "admin_test.db"),
    )


def admin():
    return bootstrap_admin(
        "GNOME Operator",
        ["credentials:issue", "customers:read"],
    )


def test_admin_bootstrap():
    result = admin()
    assert result["token"].startswith("gnadmin_")


def test_valid_admin_authorization():
    result = admin()
    identity = authorize_admin(
        result["token"], "credentials:issue"
    )
    assert identity["name"] == "GNOME Operator"


def test_missing_token_denied():
    with pytest.raises(HTTPException) as error:
        authorize_admin(None, "credentials:issue")
    assert error.value.status_code == 401


def test_customer_token_denied():
    with pytest.raises(HTTPException) as error:
        authorize_admin("gnb_customer", "credentials:issue")
    assert error.value.status_code == 401


def test_agent_token_denied():
    with pytest.raises(HTTPException) as error:
        authorize_admin("gna_agent", "credentials:issue")
    assert error.value.status_code == 401


def test_permission_denied():
    result = admin()
    with pytest.raises(HTTPException) as error:
        authorize_admin(
            result["token"], "customers:activate"
        )
    assert error.value.status_code == 403


def test_second_bootstrap_blocked():
    admin()
    with pytest.raises(ValueError):
        admin()


def test_invalid_permissions_rejected():
    with pytest.raises(ValueError):
        bootstrap_admin("Operator", ["superuser"])


def test_admin_token_not_stored_plaintext():
    result = admin()

    with connect() as db:
        row = db.execute(
            "SELECT token_hash FROM admin_credentials"
        ).fetchone()

    assert row["token_hash"] != result["token"]
    assert len(row["token_hash"]) == 64


def test_denied_permission_audited():
    result = admin()

    with pytest.raises(HTTPException):
        authorize_admin(
            result["token"], "customers:activate"
        )

    with connect() as db:
        row = db.execute(
            """
            SELECT action, result
            FROM admin_security_events
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()

    assert row["action"] == "customers:activate"
    assert row["result"] == "denied"


def test_admin_permissions_defined():
    assert "credentials:issue" in ADMIN_PERMISSIONS
    assert "credentials:revoke" in ADMIN_PERMISSIONS
