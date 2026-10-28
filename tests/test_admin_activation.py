import pytest
from fastapi import HTTPException

from app.admin_security import bootstrap_admin
from app.admin_activation import (
    verify_customer_check,
    activate_customer,
    inspect_customer_activation,
)
from app.pilot_activation import CHECKS
from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import (
    provision_workspace,
    get_workspace,
)
from app.database import connect


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "activation_admin.db"),
    )


def setup(permissions=None):
    result = provision_workspace(
        PilotApplication(
            business_name="Oak Valley",
            contact_email="oak@example.com",
        )
    )
    token = bootstrap_admin(
        "GNOME Operator",
        permissions or ["customers:activate", "customers:read"],
    )["token"]
    return result.business_id, token


def test_admin_can_verify_check():
    business_id, token = setup()
    status = verify_customer_check(
        token, business_id, CHECKS[0]
    )
    assert CHECKS[0] not in status.missing_checks


def test_missing_admin_cannot_verify():
    business_id, _ = setup()
    with pytest.raises(HTTPException) as error:
        verify_customer_check(None, business_id, CHECKS[0])
    assert error.value.status_code == 401


def test_wrong_permission_cannot_verify():
    business_id, token = setup(["customers:read"])
    with pytest.raises(HTTPException) as error:
        verify_customer_check(token, business_id, CHECKS[0])
    assert error.value.status_code == 403


def test_activation_blocked_until_checks_complete():
    business_id, token = setup()
    with pytest.raises(ValueError, match="Activation blocked"):
        activate_customer(token, business_id)
    assert get_workspace(business_id)["status"] == "pending_verification"


def test_admin_can_activate_completed_workspace():
    business_id, token = setup()
    for check in CHECKS:
        verify_customer_check(token, business_id, check)

    result = activate_customer(token, business_id)
    assert result.status == "active"
    assert get_workspace(business_id)["status"] == "active"


def test_wrong_permission_cannot_activate():
    business_id, token = setup(["customers:read"])
    with pytest.raises(HTTPException) as error:
        activate_customer(token, business_id)
    assert error.value.status_code == 403
    assert get_workspace(business_id)["status"] == "pending_verification"


def test_read_permission_can_inspect():
    business_id, token = setup(["customers:read"])
    status = inspect_customer_activation(token, business_id)
    assert status.business_id == business_id
    assert len(status.missing_checks) == len(CHECKS)


def test_invalid_check_does_not_write():
    business_id, token = setup()

    from app.pilot_activation import migrate_activation
    migrate_activation()

    with pytest.raises(ValueError):
        verify_customer_check(token, business_id, "fake_check")

    with connect() as db:
        count = db.execute(
            "SELECT COUNT(*) FROM pilot_activation_checks"
        ).fetchone()[0]

    assert count == 0
