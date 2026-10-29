from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel, Field

from app.auth import session_user
from app.database import connect
from app.agent_gateway import (
    migrate,
    provision_agent,
    revoke_agent,
)

router = APIRouter(
    prefix="/api/connectors/manage",
    tags=["Connector Management"],
)

CONNECTOR_SCOPES = {
    "leads:read",
    "appointments:read",
    "jobs:work",
}


class ConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scopes: list[str] = Field(min_length=1, max_length=3)


def current_business(session):
    user = session_user(session)
    return user["business_id"]


@router.post("", status_code=201)
def create_connector(
    data: ConnectorCreate,
    gnome_session: str | None = Cookie(default=None),
):
    business_id = current_business(gnome_session)

    if (
        len(data.scopes) != len(set(data.scopes))
        or not set(data.scopes) <= CONNECTOR_SCOPES
    ):
        raise HTTPException(
            422, "Unsupported connector permissions"
        )

    credential = provision_agent(
        business_id,
        data.name,
        data.scopes,
    )

    return {
        "id": credential["agent_id"],
        "name": data.name,
        "scopes": sorted(data.scopes),
        "token": credential["token"],
        "warning": "Store this token securely. It will not be shown again.",
    }


@router.get("")
def list_connectors(
    gnome_session: str | None = Cookie(default=None),
):
    business_id = current_business(gnome_session)
    migrate()

    with connect() as db:
        rows = db.execute(
            """
            SELECT id, name, scopes, created_at
            FROM agent_credentials
            WHERE business_id = ?
              AND revoked_at IS NULL
            ORDER BY id DESC
            """,
            (business_id,),
        ).fetchall()

    return {
        "connectors": [
            {
                "id": row["id"],
                "name": row["name"],
                "scopes": row["scopes"].split(","),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@router.post("/{connector_id}/revoke")
def revoke_connector(
    connector_id: int,
    gnome_session: str | None = Cookie(default=None),
):
    business_id = current_business(gnome_session)
    migrate()

    with connect() as db:
        row = db.execute(
            """
            SELECT id FROM agent_credentials
            WHERE id = ?
              AND business_id = ?
              AND revoked_at IS NULL
            """,
            (connector_id, business_id),
        ).fetchone()

        if row is None:
            raise HTTPException(
                404, "Connector not found"
            )

        revoke_agent(connector_id)

    return {
        "id": connector_id,
        "revoked": True,
    }
