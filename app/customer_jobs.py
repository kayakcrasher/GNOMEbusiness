import json

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel, Field

from app.auth import session_user
from app.database import connect
from app.agent_workstation import (
    migrate,
    encode,
    record,
)

router = APIRouter(
    prefix="/api/customer/jobs",
    tags=["Customer Jobs"],
)

ALLOWED_KINDS = {
    "lead:analyze",
    "lead:process",
    "outreach:draft",
    "appointment:research",
}


class CustomerJobCreate(BaseModel):
    agent_id: int = Field(gt=0)
    kind: str = Field(min_length=1, max_length=80)
    instructions: str = Field(min_length=1, max_length=2000)


def owner_business(token):
    return session_user(token)["business_id"]


@router.post("", status_code=201)
def create_customer_job(
    data: CustomerJobCreate,
    gnome_session: str | None = Cookie(default=None),
):
    business_id = owner_business(gnome_session)
    migrate()

    if data.kind not in ALLOWED_KINDS:
        raise HTTPException(422, "Unsupported job type")

    with connect() as db:
        agent = db.execute(
            """
            SELECT id, scopes
            FROM agent_credentials
            WHERE id = ?
              AND business_id = ?
              AND revoked_at IS NULL
            """,
            (data.agent_id, business_id),
        ).fetchone()

        if agent is None:
            raise HTTPException(404, "Agent not found")

        if "jobs:work" not in agent["scopes"].split(","):
            raise HTTPException(
                403, "Agent lacks jobs:work permission"
            )

        instructions = encode({
            "request": data.instructions.strip(),
        })

        cursor = db.execute(
            """
            INSERT INTO agent_jobs
            (business_id, created_by, kind, instructions)
            VALUES (?, ?, ?, ?)
            """,
            (
                business_id,
                agent["id"],
                data.kind,
                instructions,
            ),
        )

    return {
        "id": cursor.lastrowid,
        "status": "queued",
    }


@router.get("")
def list_customer_jobs(
    gnome_session: str | None = Cookie(default=None),
):
    business_id = owner_business(gnome_session)
    migrate()

    with connect() as db:
        rows = db.execute(
            """
            SELECT *
            FROM agent_jobs
            WHERE business_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (business_id,),
        ).fetchall()

    return {"jobs": [record(row) for row in rows]}
