from datetime import datetime, timezone

from fastapi import APIRouter, Header

from app.agent_gateway import (
    authorize,
    bearer_token,
)
from app.database import connect

router = APIRouter(
    prefix="/api/agents",
    tags=["Agent Health"],
)


def migrate():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_heartbeats (
                agent_id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                last_seen TEXT NOT NULL,
                FOREIGN KEY (agent_id)
                    REFERENCES agent_credentials(id)
            )
        """)


@router.post("/heartbeat")
def heartbeat(
    authorization: str | None = Header(default=None),
):
    agent = authorize(
        bearer_token(authorization),
        "jobs:work",
    )

    migrate()

    now = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        db.execute(
            """
            INSERT INTO agent_heartbeats
            (agent_id, business_id, last_seen)
            VALUES (?, ?, ?)
            ON CONFLICT(agent_id)
            DO UPDATE SET
                last_seen = excluded.last_seen,
                business_id = excluded.business_id
            """,
            (
                agent["agent_id"],
                agent["business_id"],
                now,
            ),
        )

    return {
        "agent_id": agent["agent_id"],
        "status": "online",
        "last_seen": now,
    }
