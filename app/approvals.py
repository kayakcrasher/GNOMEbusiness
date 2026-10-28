import json

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.database import connect
from app.agent_gateway import (
    migrate as agent_migrate,
    authorize,
    bearer_token,
)
from app.security import authenticate

router = APIRouter(
    prefix="/api/approvals",
    tags=["Agent Approvals"],
)

ALLOWED_ACTIONS = {
    "outreach:draft",
    "lead:review",
    "appointment:propose",
}


def migrate():
    agent_migrate()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_proposals (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                agent_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                title TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by TEXT,
                reviewed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id),
                FOREIGN KEY (agent_id)
                    REFERENCES agent_credentials(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS approval_events (
                id INTEGER PRIMARY KEY,
                proposal_id INTEGER NOT NULL,
                business_id INTEGER NOT NULL,
                actor TEXT NOT NULL,
                event TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposal_id)
                    REFERENCES agent_proposals(id)
            )
        """)


class ProposalCreate(BaseModel):
    action: str
    title: str = Field(min_length=1, max_length=200)
    payload: dict = Field(default_factory=dict)


class Decision(BaseModel):
    decision: str


def human_business(x_api_key):
    return authenticate(x_api_key)


@router.post("/proposals", status_code=201)
def submit_proposal(
    data: ProposalCreate,
    authorization: str | None = Header(default=None),
):
    agent = authorize(
        bearer_token(authorization),
        "proposals:create",
    )

    if data.action not in ALLOWED_ACTIONS:
        raise HTTPException(
            422, "Unsupported proposal action"
        )

    encoded = json.dumps(
        data.payload,
        ensure_ascii=False,
        allow_nan=False,
    )

    if len(encoded.encode("utf-8")) > 10000:
        raise HTTPException(
            422, "Proposal payload too large"
        )

    migrate()

    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO agent_proposals
            (business_id, agent_id, action, title, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                agent["business_id"],
                agent["agent_id"],
                data.action,
                data.title,
                encoded,
            ),
        )

        proposal_id = cursor.lastrowid

        db.execute(
            """
            INSERT INTO approval_events
            (proposal_id, business_id, actor, event)
            VALUES (?, ?, ?, 'submitted')
            """,
            (
                proposal_id,
                agent["business_id"],
                f"agent:{agent['agent_id']}",
            ),
        )

    return {
        "id": proposal_id,
        "status": "pending",
    }


@router.get("")
def list_proposals(
    x_api_key: str | None = Header(default=None),
):
    business_id = human_business(x_api_key)
    migrate()

    with connect() as db:
        rows = db.execute(
            """
            SELECT p.id, p.action, p.title, p.payload,
                   p.status, p.created_at,
                   p.reviewed_by, p.reviewed_at,
                   a.name AS agent_name
            FROM agent_proposals p
            JOIN agent_credentials a ON a.id = p.agent_id
            WHERE p.business_id = ?
            ORDER BY p.id DESC
            LIMIT 100
            """,
            (business_id,),
        ).fetchall()

    proposals = []

    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        proposals.append(item)

    return {"proposals": proposals}


@router.post("/{proposal_id}/decision")
def decide_proposal(
    proposal_id: int,
    data: Decision,
    x_api_key: str | None = Header(default=None),
):
    business_id = human_business(x_api_key)

    if data.decision not in {"approved", "rejected"}:
        raise HTTPException(
            422, "Decision must be approved or rejected"
        )

    migrate()

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE agent_proposals
            SET status = ?,
                reviewed_by = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND business_id = ?
              AND status = 'pending'
            """,
            (
                data.decision,
                "business-api-key",
                proposal_id,
                business_id,
            ),
        )

        if cursor.rowcount != 1:
            existing = db.execute(
                """
                SELECT status
                FROM agent_proposals
                WHERE id = ? AND business_id = ?
                """,
                (proposal_id, business_id),
            ).fetchone()

            if existing is None:
                raise HTTPException(404, "Proposal not found")

            raise HTTPException(
                409, "Proposal already reviewed"
            )

        db.execute(
            """
            INSERT INTO approval_events
            (proposal_id, business_id, actor, event)
            VALUES (?, ?, ?, ?)
            """,
            (
                proposal_id,
                business_id,
                "business-api-key",
                data.decision,
            ),
        )

    return {
        "id": proposal_id,
        "status": data.decision,
        "executed": False,
    }
