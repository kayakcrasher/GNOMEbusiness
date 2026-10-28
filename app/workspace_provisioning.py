from dataclasses import dataclass

from app.database import connect, initialize
from app.pilot_onboarding import (
    prepare_pilot,
    validate_application,
)


@dataclass
class WorkspaceResult:
    business_id: int
    business_name: str
    status: str
    pilot: dict


def migrate():
    initialize()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS pilot_workspaces (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL UNIQUE,
                contact_email TEXT NOT NULL,
                plan TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_verification',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                activated_at TEXT,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id)
            )
        """)


def provision_workspace(application, start_date=None):
    errors = validate_application(application)

    if errors:
        raise ValueError(", ".join(errors))

    pilot = prepare_pilot(application, start_date)
    migrate()

    name = application.business_name.strip()
    email = application.contact_email.strip()

    with connect() as db:
        existing = db.execute(
            """
            SELECT w.business_id
            FROM pilot_workspaces w
            WHERE lower(w.contact_email) = lower(?)
              AND lower(w.plan) = lower(?)
              AND w.status = 'pending_verification'
            """,
            (email, application.plan),
        ).fetchone()

        if existing:
            raise ValueError(
                "Pending pilot already exists for this contact and plan"
            )

        cursor = db.execute(
            "INSERT INTO businesses (name) VALUES (?)",
            (name,),
        )
        business_id = cursor.lastrowid

        db.execute(
            """
            INSERT INTO pilot_workspaces
            (business_id, contact_email, plan)
            VALUES (?, ?, ?)
            """,
            (business_id, email, application.plan),
        )

    return WorkspaceResult(
        business_id=business_id,
        business_name=name,
        status="pending_verification",
        pilot=pilot,
    )


def get_workspace(business_id):
    migrate()

    with connect() as db:
        row = db.execute(
            """
            SELECT w.business_id, b.name AS business_name,
                   w.contact_email, w.plan, w.status,
                   w.created_at, w.activated_at
            FROM pilot_workspaces w
            JOIN businesses b ON b.id = w.business_id
            WHERE w.business_id = ?
            """,
            (business_id,),
        ).fetchone()

    return dict(row) if row else None
