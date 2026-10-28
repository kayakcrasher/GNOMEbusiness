import sqlite3

import pytest

from app.database import connect
from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import provision_workspace
from app.credential_lifecycle import (
    issue_owner_key,
    issue_agent_token,
    migrate,
)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "atomic.db"),
    )


def active_business():
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

    return result.business_id


def block_audit_writes():
    migrate()

    with connect() as db:
        db.execute("""
            CREATE TRIGGER block_credential_audit
            BEFORE INSERT ON credential_events
            BEGIN
                SELECT RAISE(ABORT, 'audit unavailable');
            END
        """)


def count_rows(table):
    with connect() as db:
        return db.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]


def test_owner_issuance_records_audit():
    business_id = active_business()

    key = issue_owner_key(business_id, "operator")

    assert key.startswith("gnb_")
    assert count_rows("api_keys") == 1
    assert count_rows("credential_events") == 1


def test_agent_issuance_records_audit():
    business_id = active_business()

    result = issue_agent_token(
        business_id,
        "Leadkeeper",
        ["leads:read"],
        "operator",
    )

    assert result["token"].startswith("gna_")
    assert count_rows("agent_credentials") == 1
    assert count_rows("credential_events") == 1


def test_owner_rollback_on_audit_failure():
    business_id = active_business()
    block_audit_writes()

    with pytest.raises(sqlite3.DatabaseError):
        issue_owner_key(business_id, "operator")

    assert count_rows("api_keys") == 0
    assert count_rows("credential_events") == 0


def test_agent_rollback_on_audit_failure():
    business_id = active_business()
    block_audit_writes()

    with pytest.raises(sqlite3.DatabaseError):
        issue_agent_token(
            business_id,
            "Leadkeeper",
            ["leads:read"],
            "operator",
        )

    assert count_rows("agent_credentials") == 0
    assert count_rows("credential_events") == 0
