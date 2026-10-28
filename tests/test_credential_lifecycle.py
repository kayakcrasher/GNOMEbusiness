import pytest
from fastapi import HTTPException

from app.database import connect
from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import provision_workspace
from app.credential_lifecycle import (
    issue_owner_key,
    issue_agent_token,
    revoke_credential,
    credential_inventory,
)
from app.security import authenticate
from app.agent_gateway import authorize


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "credentials.db"),
    )


def customer(active=True, email="oak@example.com"):
    result = provision_workspace(
        PilotApplication(
            business_name="Oak Valley",
            contact_email=email,
        )
    )

    if active:
        with connect() as db:
            db.execute(
                """
                UPDATE pilot_workspaces
                SET status = 'active'
                WHERE business_id = ?
                """,
                (result.business_id,),
            )

    return result.business_id


def test_pending_owner_issuance_denied():
    business_id = customer(active=False)

    with pytest.raises(HTTPException):
        issue_owner_key(business_id, "operator")


def test_pending_agent_issuance_denied():
    business_id = customer(active=False)

    with pytest.raises(HTTPException):
        issue_agent_token(
            business_id,
            "Leadkeeper",
            ["leads:read"],
            "operator",
        )


def test_active_owner_key_works():
    business_id = customer()
    key = issue_owner_key(business_id, "operator")

    assert authenticate(key) == business_id


def test_active_agent_token_works():
    business_id = customer()

    result = issue_agent_token(
        business_id,
        "Leadkeeper",
        ["leads:read"],
        "operator",
    )

    assert authorize(
        result["token"], "leads:read"
    )["business_id"] == business_id


def test_owner_revocation():
    business_id = customer()
    key = issue_owner_key(business_id, "operator")

    inventory = credential_inventory(business_id)
    key_id = inventory["owners"][0]["id"]

    assert revoke_credential(
        business_id, "owner", key_id, "operator"
    )

    with pytest.raises(HTTPException):
        authenticate(key)


def test_agent_revocation():
    business_id = customer()

    agent = issue_agent_token(
        business_id,
        "Leadkeeper",
        ["leads:read"],
        "operator",
    )

    assert revoke_credential(
        business_id,
        "agent",
        agent["agent_id"],
        "operator",
    )

    with pytest.raises(HTTPException):
        authorize(agent["token"], "leads:read")


def test_cross_tenant_revocation_denied():
    first = customer()
    second = customer(email="pine@example.com")

    key = issue_owner_key(first, "operator")
    key_id = credential_inventory(first)["owners"][0]["id"]

    assert not revoke_credential(
        second, "owner", key_id, "operator"
    )

    assert authenticate(key) == first


def test_inventory_does_not_expose_secrets():
    business_id = customer()

    key = issue_owner_key(business_id, "operator")
    agent = issue_agent_token(
        business_id,
        "Leadkeeper",
        ["leads:read"],
        "operator",
    )

    inventory = credential_inventory(business_id)
    representation = str(inventory)

    assert key not in representation
    assert agent["token"] not in representation
    assert "key_hash" not in representation
    assert "token_hash" not in representation


def test_operator_required():
    business_id = customer()

    with pytest.raises(ValueError):
        issue_owner_key(business_id, "")


def test_audit_records_issuance_and_revocation():
    business_id = customer()
    issue_owner_key(business_id, "operator")
    key_id = credential_inventory(business_id)["owners"][0]["id"]

    revoke_credential(
        business_id, "owner", key_id, "operator"
    )

    with connect() as db:
        events = db.execute(
            """
            SELECT action FROM credential_events
            WHERE business_id = ?
            ORDER BY id
            """,
            (business_id,),
        ).fetchall()

    assert [row["action"] for row in events] == [
        "issued", "revoked"
    ]
