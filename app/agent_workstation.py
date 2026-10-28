import json

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.database import connect
from app.agent_gateway import (
    authorize,
    bearer_token,
    migrate as agent_migrate,
)

router = APIRouter(
    prefix="/api/workstation",
    tags=["Agent Workstation"],
)

MAX_JSON_BYTES = 10000


def migrate():
    agent_migrate()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_jobs (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                claimed_by INTEGER,
                kind TEXT NOT NULL,
                instructions TEXT NOT NULL,
                result TEXT,
                status TEXT NOT NULL DEFAULT 'queued'
                    CHECK (
                        status IN (
                            'queued',
                            'working',
                            'completed'
                        )
                    ),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                claimed_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id),
                FOREIGN KEY (created_by)
                    REFERENCES agent_credentials(id),
                FOREIGN KEY (claimed_by)
                    REFERENCES agent_credentials(id)
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_jobs_queue
            ON agent_jobs(business_id, status, id)
        """)


class JobCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=80)
    instructions: dict


class JobComplete(BaseModel):
    result: dict


def encode(value):
    try:
        data = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        raise HTTPException(422, "Invalid JSON payload")

    if len(data.encode("utf-8")) > MAX_JSON_BYTES:
        raise HTTPException(422, "Payload too large")

    return data


def identity(authorization):
    return authorize(
        bearer_token(authorization),
        "jobs:work",
    )


def record(row):
    item = dict(row)
    item["instructions"] = json.loads(
        item["instructions"]
    )

    if item["result"] is not None:
        item["result"] = json.loads(item["result"])

    return item


@router.post("/jobs", status_code=201)
def create_job(
    data: JobCreate,
    authorization: str | None = Header(default=None),
):
    agent = identity(authorization)
    migrate()

    # Initial job types are deliberately read-only
    # or draft-producing. No external side effects.
    allowed = {
        "lead:analyze",
        "lead:process",
        "outreach:draft",
        "appointment:research",
    }

    if data.kind not in allowed:
        raise HTTPException(422, "Unsupported job type")

    instructions = encode(data.instructions)

    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO agent_jobs
            (business_id, created_by, kind, instructions)
            VALUES (?, ?, ?, ?)
            """,
            (
                agent["business_id"],
                agent["agent_id"],
                data.kind,
                instructions,
            ),
        )

        job_id = cursor.lastrowid

    return {
        "id": job_id,
        "status": "queued",
    }


@router.get("/jobs")
def list_jobs(
    authorization: str | None = Header(default=None),
):
    agent = identity(authorization)
    migrate()

    with connect() as db:
        rows = db.execute(
            """
            SELECT *
            FROM agent_jobs
            WHERE business_id = ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (agent["business_id"],),
        ).fetchall()

    return {
        "jobs": [record(row) for row in rows]
    }


@router.post("/jobs/{job_id}/claim")
def claim_job(
    job_id: int,
    authorization: str | None = Header(default=None),
):
    agent = identity(authorization)
    migrate()

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE agent_jobs
            SET status = 'working',
                claimed_by = ?,
                claimed_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND business_id = ?
              AND status = 'queued'
            """,
            (
                agent["agent_id"],
                job_id,
                agent["business_id"],
            ),
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                409, "Job unavailable for claim"
            )

    return {
        "id": job_id,
        "status": "working",
        "claimed_by": agent["agent_id"],
    }


@router.post("/jobs/{job_id}/complete")
def complete_job(
    job_id: int,
    data: JobComplete,
    authorization: str | None = Header(default=None),
):
    agent = identity(authorization)
    migrate()
    result = encode(data.result)

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE agent_jobs
            SET status = 'completed',
                result = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND business_id = ?
              AND claimed_by = ?
              AND status = 'working'
            """,
            (
                result,
                job_id,
                agent["business_id"],
                agent["agent_id"],
            ),
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                409, "Job cannot be completed"
            )

    return {
        "id": job_id,
        "status": "completed",
    }
