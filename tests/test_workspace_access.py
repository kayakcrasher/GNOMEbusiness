import pytest
from fastapi import HTTPException

from app.database import connect, initialize
from app.pilot_onboarding import PilotApplication
from app.workspace_provisioning import provision_workspace
from app.workspace_access import require_active_workspace


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "access_test.db"),
    )


def create_pilot():
    return provision_workspace(
        PilotApplication(
            business_name="Oak Valley",
            contact_email="oak@example.com",
        )
    ).business_id


def test_pending_workspace_denied():
    business_id = create_pilot()

    with pytest.raises(HTTPException) as error:
        require_active_workspace(business_id)

    assert error.value.status_code == 403


def test_active_workspace_allowed():
    business_id = create_pilot()

    with connect() as db:
        db.execute(
            """
            UPDATE pilot_workspaces
            SET status = 'active'
            WHERE business_id = ?
            """,
            (business_id,),
        )

    assert require_active_workspace(business_id) == business_id


def test_suspended_workspace_denied():
    business_id = create_pilot()

    with connect() as db:
        db.execute(
            """
            UPDATE pilot_workspaces
            SET status = 'suspended'
            WHERE business_id = ?
            """,
            (business_id,),
        )

    with pytest.raises(HTTPException) as error:
        require_active_workspace(business_id)

    assert error.value.status_code == 403


def test_legacy_development_business_allowed():
    initialize()

    with connect() as db:
        cursor = db.execute(
            "INSERT INTO businesses (name) VALUES (?)",
            ("GNOME Development",),
        )
        business_id = cursor.lastrowid

    assert require_active_workspace(business_id) == business_id
