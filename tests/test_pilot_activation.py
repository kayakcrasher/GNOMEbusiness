import pytest

from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import (
    provision_workspace,
    get_workspace,
)
from app.pilot_activation import (
    CHECKS,
    verify_check,
    activation_status,
    activate_workspace,
)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "activation_test.db"),
    )


def new_workspace():
    application = PilotApplication(
        business_name="Oak Valley",
        contact_email="oak@example.com",
    )
    return provision_workspace(application).business_id


def test_initially_pending():
    business_id = new_workspace()
    status = activation_status(business_id)
    assert status.status == "pending_verification"
    assert len(status.missing_checks) == len(CHECKS)


def test_activation_blocked_without_checks():
    business_id = new_workspace()
    with pytest.raises(ValueError, match="Activation blocked"):
        activate_workspace(business_id)


def test_verification_reduces_missing_checks():
    business_id = new_workspace()
    verify_check(business_id, "payment_verified", "operator")
    assert "payment_verified" not in (
        activation_status(business_id).missing_checks
    )


def test_invalid_check_rejected():
    business_id = new_workspace()
    with pytest.raises(ValueError):
        verify_check(business_id, "skip_security", "operator")


def test_missing_verifier_rejected():
    business_id = new_workspace()
    with pytest.raises(ValueError):
        verify_check(business_id, "payment_verified", "")


def test_full_activation():
    business_id = new_workspace()

    for check in CHECKS:
        verify_check(business_id, check, "test-operator")

    result = activate_workspace(business_id)

    assert result.status == "active"
    assert get_workspace(business_id)["status"] == "active"


def test_cannot_activate_twice():
    business_id = new_workspace()

    for check in CHECKS:
        verify_check(business_id, check, "test-operator")

    activate_workspace(business_id)

    with pytest.raises(ValueError, match="not pending"):
        activate_workspace(business_id)


def test_checks_do_not_cross_tenants():
    first = new_workspace()

    second = provision_workspace(
        PilotApplication(
            business_name="Pine Ridge",
            contact_email="pine@example.com",
        )
    ).business_id

    for check in CHECKS:
        verify_check(first, check, "test-operator")

    assert len(
        activation_status(second).missing_checks
    ) == len(CHECKS)

    with pytest.raises(ValueError, match="Activation blocked"):
        activate_workspace(second)
