import hashlib
import secrets

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.database import connect, initialize

router = APIRouter(
    prefix="/api/agents",
    tags=["Agent Gateway"],
)

SCOPES = {
    "leads:read",
    "appointments:read",
    "proposals:create",
    "jobs:work",
}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def migrate():
    initialize()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_credentials (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                scopes TEXT NOT NULL,
                revoked_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_audit (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER NOT NULL,
                business_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id)
                    REFERENCES agent_credentials(id)
            )
        """)


def provision_agent(business_id, name, scopes):
    """
    Trusted server-side provisioning only.
    Never expose this function as a public endpoint.
    """
    migrate()

    if not name or not name.strip():
        raise ValueError("Agent name required")

    requested = set(scopes)

    if not requested or not requested <= SCOPES:
        raise ValueError("Unsupported permissions")

    token = "gna_" + secrets.token_urlsafe(32)

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if business is None:
            raise ValueError("Business not found")

        cursor = db.execute(
            """
            INSERT INTO agent_credentials
            (business_id, name, token_hash, scopes)
            VALUES (?, ?, ?, ?)
            """,
            (
                business_id,
                name.strip(),
                digest(token),
                ",".join(sorted(requested)),
            ),
        )

        agent_id = cursor.lastrowid

    return {
        "agent_id": agent_id,
        "token": token,
    }


def audit(db, agent, action, result):
    db.execute(
        """
        INSERT INTO agent_audit
        (agent_id, business_id, action, result)
        VALUES (?, ?, ?, ?)
        """,
        (
            agent["id"],
            agent["business_id"],
            action,
            result,
        ),
    )


def authorize(token, scope):
    migrate()

    if not token or not token.startswith("gna_"):
        raise HTTPException(401, "Agent credential required")

    with connect() as db:
        agent = db.execute(
            """
            SELECT id, business_id, name, scopes
            FROM agent_credentials
            WHERE token_hash = ?
              AND revoked_at IS NULL
            """,
            (digest(token),),
        ).fetchone()

        if agent is None:
            raise HTTPException(401, "Invalid agent credential")

        if scope not in agent["scopes"].split(","):
            audit(db, agent, scope, "denied")
            raise HTTPException(403, "Permission denied")

        audit(db, agent, scope, "allowed")

    from app.workspace_access import require_active_workspace
    require_active_workspace(agent["business_id"])

    return {
        "agent_id": agent["id"],
        "business_id": agent["business_id"],
        "name": agent["name"],
    }


def bearer_token(authorization):
    if not authorization:
        return None

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


@router.get("/me")
def agent_identity(
    authorization: str | None = Header(default=None),
):
    agent = authorize(
        bearer_token(authorization),
        "leads:read",
    )

    return {
        "agent_id": agent["agent_id"],
        "name": agent["name"],
        "business_id": agent["business_id"],
    }


@router.get("/leads")
def agent_leads(
    authorization: str | None = Header(default=None),
    limit: int = 25,
):
    agent = authorize(
        bearer_token(authorization),
        "leads:read",
    )

    limit = max(1, min(limit, 100))

    with connect() as db:
        rows = db.execute(
            """
            SELECT id, company, status, created_at
            FROM leads
            WHERE business_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (agent["business_id"], limit),
        ).fetchall()

    return {
        "business_id": agent["business_id"],
        "leads": [dict(row) for row in rows],
    }


@router.get("/appointments")
def agent_appointments(
    authorization: str | None = Header(default=None),
    limit: int = 25,
):
    agent = authorize(
        bearer_token(authorization),
        "appointments:read",
    )

    from app.appointments.api import migrate as booking_migrate
    booking_migrate()

    limit = max(1, min(limit, 100))

    with connect() as db:
        rows = db.execute(
            """
            SELECT id, lead_id, title, starts_at, status
            FROM appointments
            WHERE business_id = ?
            ORDER BY starts_at ASC
            LIMIT ?
            """,
            (agent["business_id"], limit),
        ).fetchall()

    return {
        "business_id": agent["business_id"],
        "appointments": [dict(row) for row in rows],
    }


def revoke_agent(agent_id):
    migrate()

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE agent_credentials
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE id = ? AND revoked_at IS NULL
            """,
            (agent_id,),
        )

        return cursor.rowcount == 1
