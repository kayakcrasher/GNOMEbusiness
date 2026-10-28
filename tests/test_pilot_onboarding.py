from datetime import date

import pytest

from app.pilot_onboarding import (
    PilotApplication,
    prepare_pilot,
    validate_application,
)


def sample(**overrides):
    values = {
        "business_name": "Oak Valley Services",
        "contact_email": "owner@example.com",
        "plan": "basic",
    }
    values.update(overrides)
    return PilotApplication(**values)


def test_valid_application():
    assert validate_application(sample()) == []


def test_invalid_business_name():
    assert "invalid_business_name" in validate_application(
        sample(business_name="")
    )


def test_invalid_email():
    assert "invalid_email" in validate_application(
        sample(contact_email="not-an-email")
    )


def test_unknown_plan():
    assert "invalid_plan" in validate_application(
        sample(plan="enterprise")
    )


def test_pilot_pricing():
    pilot = prepare_pilot(
        sample(), date(2026, 11, 1)
    )
    assert pilot["pilot_price"] == 49
    assert pilot["monthly_price_after_pilot"] == 29


def test_growth_pricing():
    pilot = prepare_pilot(
        sample(plan="growth"), date(2026, 11, 1)
    )
    assert pilot["monthly_price_after_pilot"] == 59
    assert pilot["monthly_lead_limit"] == 200


def test_pilot_duration():
    pilot = prepare_pilot(
        sample(), date(2026, 11, 1)
    )
    assert pilot["end_date"] == "2026-11-15"


def test_pilot_not_automatically_activated():
    pilot = prepare_pilot(sample())
    assert pilot["status"] == "pending_verification"
    assert pilot["payment_confirmed"] is False
    assert pilot["workspace_provisioned"] is False


def test_invalid_application_rejected():
    with pytest.raises(ValueError):
        prepare_pilot(sample(contact_email="invalid"))
