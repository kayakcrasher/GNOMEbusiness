from fastapi import APIRouter, Cookie, Query

from app.auth import session_user
from app.database import connect
from app.agent_workstation import migrate

router = APIRouter(
    prefix="/api/customer/operations",
    tags=["Agent Operations"],
)


@router.get("")
def operations(
    gnome_session: str | None = Cookie(default=None),
    limit: int = Query(default=50, ge=1, le=100),
):
    business_id = session_user(
        gnome_session
    )["business_id"]

    migrate()

    with connect() as db:
        agents = db.execute(
            """
            SELECT id, name, scopes, created_at
            FROM agent_credentials
            WHERE business_id = ?
              AND revoked_at IS NULL
            ORDER BY id
            """,
            (business_id,),
        ).fetchall()

        jobs = db.execute(
            """
            SELECT j.id, j.kind, j.status,
                   j.created_by, j.claimed_by,
                   j.created_at, j.claimed_at,
                   j.completed_at,
                   creator.name AS created_by_name,
                   worker.name AS claimed_by_name
            FROM agent_jobs j
            LEFT JOIN agent_credentials creator
              ON creator.id = j.created_by
            LEFT JOIN agent_credentials worker
              ON worker.id = j.claimed_by
            WHERE j.business_id = ?
            ORDER BY j.id DESC
            LIMIT ?
            """,
            (business_id, limit),
        ).fetchall()

        counts = db.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM agent_jobs
            WHERE business_id = ?
            GROUP BY status
            """,
            (business_id,),
        ).fetchall()

    totals = {
        "queued": 0,
        "working": 0,
        "completed": 0,
    }

    for row in counts:
        totals[row["status"]] = row["total"]

    return {
        "summary": totals,
        "agents": [
            {
                **dict(agent),
                "scopes": agent["scopes"].split(","),
            }
            for agent in agents
        ],
        "jobs": [dict(job) for job in jobs],
    }
