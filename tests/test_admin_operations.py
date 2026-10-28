import pytest
from fastapi import HTTPException

from app.database import connect
from app.admin_security import bootstrap_admin
from app.admin_operations import (
    issue_customer_owner_key,
    issue_customer_agent_token,
    revoke_customer_credential,
    inspect_customer_credentials,
)
from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import provision_workspace
from app.security import authenticate
from app.agent_gateway import authorize


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "admin_ops.db"),
    )


def setup():
    result = provision_workspace(
        PilotApplication(
            business_name="Oak Valley",
            contact_email="oak@example.com",
        )
    )

    with connect() as db:
        db.execute(
            """
            UPDATE pilot_workspaces
            SET status = 'active'
            WHERE business_id = ?
            """,
            (result.business_id,),
        )

    token = bootstrap_admin(
        "GNOME Operator",
        [
            "credentials:issue",
            "credentials:revoke",
            "customers:read",
        ],
    )["token"]

    return result.business_id, token


def test_authorized_owner_issuance():
    business_id, token = setup()

    key = issue_customer_owner_key(
        token, business_id
    )

    assert authenticate(key) == business_id


def test_missing_admin_denied():
    business_id, _ = setup()

    with pytest.raises(HTTPException) as error:
        issue_customer_owner_key(None, business_id)

    assert error.value.status_code == 401


def test_customer_key_cannot_issue():
    business_id, token = setup()

    customer_key = issue_customer_owner_key(
        token, business_id
    )

    with pytest.raises(HTTPException) as error:
        issue_customer_owner_key(
            customer_key, business_id
        )

    assert error.value.status_code == 401


def test_authorized_agent_issuance():
    business_id, token = setup()

    agent = issue_customer_agent_token(
        token,
        business_id,
        "Leadkeeper",
        ["leads:read"],
    )

    assert authorize(
        agent["token"], "leads:read"
    )["business_id"] == business_id


def test_agent_cannot_issue_owner_key():
    business_id, token = setup()

    agent = issue_customer_agent_token(
        token,
        business_id,
        "Leadkeeper",
        ["leads:read"],
    )

    with pytest.raises(HTTPException) as error:
        issue_customer_owner_key(
            agent["token"], business_id
        )

    assert error.value.status_code == 401


def test_authorized_revoke():
    business_id, token = setup()

    key = issue_customer_owner_key(
        token, business_id
    )

    inventory = inspect_customer_credentials(
        token, business_id
    )

    key_id = inventory["owners"][0]["id"]

    assert revoke_customer_credential(
        token, business_id, "owner", key_id
    )

    with pytest.raises(HTTPException):
        authenticate(key)


def test_missing_admin_cannot_revoke():
    business_id, token = setup()

    issue_customer_owner_key(token, business_id)

    key_id = inspect_customer_credentials(
        token, business_id
    )["owners"][0]["id"]

    with pytest.raises(HTTPException) as error:
        revoke_customer_credential(
            None, business_id, "owner", key_id
        )

    assert error.value.status_code == 401


def test_read_permission_required():
    business_id, token = setup()

    assert inspect_customer_credentials(
        token, business_id
    )["owners"] == []


def test_issue_only_admin_cannot_revoke():
    business_id, token = setup()

    with connect() as db:
        db.execute(
            """
            UPDATE admin_credentials
            SET permissions = 'credentials:issue'
            """
        )

    with pytest.raises(HTTPException) as error:
        revoke_customer_credential(
            token,
            business_id,
            "owner",
            1,
        )

    assert error.value.status_code == 403


def test_unauthorized_inventory_denied():
    business_id, _ = setup()

    with pytest.raises(HTTPException) as error:
        inspect_customer_credentials(
            None, business_id
        )

    assert error.value.status_code == 401
