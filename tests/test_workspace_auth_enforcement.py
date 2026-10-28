import pytest
from fastapi import HTTPException

from app.database import connect
from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import provision_workspace
from app.security import create_key, authenticate
from app.agent_gateway import provision_agent, authorize


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "auth_test.db"),
    )


def setup_customer():
    result = provision_workspace(
        PilotApplication(
            business_name="Oak Valley",
            contact_email="oak@example.com",
        )
    )

    business_id = result.business_id
    owner_key = create_key(business_id)

    agent_token = provision_agent(
        business_id,
        "Leadkeeper",
        ["leads:read"],
    )["token"]

    return business_id, owner_key, agent_token


def set_status(business_id, status):
    with connect() as db:
        db.execute(
            """
            UPDATE pilot_workspaces
            SET status = ?
            WHERE business_id = ?
            """,
            (status, business_id),
        )


def test_pending_owner_denied():
    _, key, _ = setup_customer()

    with pytest.raises(HTTPException) as error:
        authenticate(key)

    assert error.value.status_code == 403


def test_pending_agent_denied():
    _, _, token = setup_customer()

    with pytest.raises(HTTPException) as error:
        authorize(token, "leads:read")

    assert error.value.status_code == 403


def test_active_owner_allowed():
    business_id, key, _ = setup_customer()
    set_status(business_id, "active")

    assert authenticate(key) == business_id


def test_active_agent_allowed():
    business_id, _, token = setup_customer()
    set_status(business_id, "active")

    result = authorize(token, "leads:read")
    assert result["business_id"] == business_id


def test_suspended_owner_denied():
    business_id, key, _ = setup_customer()
    set_status(business_id, "suspended")

    with pytest.raises(HTTPException) as error:
        authenticate(key)

    assert error.value.status_code == 403


def test_suspended_agent_denied():
    business_id, _, token = setup_customer()
    set_status(business_id, "suspended")

    with pytest.raises(HTTPException) as error:
        authorize(token, "leads:read")

    assert error.value.status_code == 403
