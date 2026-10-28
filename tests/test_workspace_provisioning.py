import pytest

from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import (
    get_workspace,
    provision_workspace,
)
from app.database import connect


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "workspace_test.db"),
    )


def application(name, email):
    return PilotApplication(
        business_name=name,
        contact_email=email,
        plan="basic",
    )


def test_workspace_created_pending():
    result = provision_workspace(
        application("Oak Valley", "oak@example.com")
    )

    assert result.business_id > 0
    assert result.status == "pending_verification"


def test_separate_customers_get_separate_business_ids():
    first = provision_workspace(
        application("Oak Valley", "oak@example.com")
    )
    second = provision_workspace(
        application("Pine Ridge", "pine@example.com")
    )

    assert first.business_id != second.business_id


def test_workspace_can_be_retrieved():
    result = provision_workspace(
        application("Oak Valley", "oak@example.com")
    )

    workspace = get_workspace(result.business_id)

    assert workspace["business_name"] == "Oak Valley"
    assert workspace["plan"] == "basic"


def test_duplicate_pending_application_rejected():
    applicant = application(
        "Oak Valley", "oak@example.com"
    )

    provision_workspace(applicant)

    with pytest.raises(ValueError):
        provision_workspace(applicant)


def test_invalid_application_creates_nothing():
    with pytest.raises(ValueError):
        provision_workspace(
            application("", "invalid")
        )

    with connect() as db:
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }

        if "businesses" in tables:
            count = db.execute(
                "SELECT COUNT(*) FROM businesses"
            ).fetchone()[0]
            assert count == 0


def test_workspace_has_no_credentials():
    result = provision_workspace(
        application("Oak Valley", "oak@example.com")
    )

    with connect() as db:
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }

        assert "api_keys" not in tables
        assert "agent_credentials" not in tables

    assert get_workspace(result.business_id)["status"] == (
        "pending_verification"
    )


def test_missing_workspace():
    assert get_workspace(99999) is None
