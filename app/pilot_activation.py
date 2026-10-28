from dataclasses import dataclass

from app.database import connect
from app.workspace_provisioning import migrate, get_workspace


CHECKS = (
    "payment_verified",
    "agreement_accepted",
    "ownership_verified",
    "tenant_isolation_verified",
    "approval_workflow_verified",
    "data_policy_verified",
)


@dataclass
class ActivationResult:
    business_id: int
    status: str
    missing_checks: list


def migrate_activation():
    migrate()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS pilot_activation_checks (
                business_id INTEGER NOT NULL,
                check_name TEXT NOT NULL,
                verified_by TEXT NOT NULL,
                verified_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (business_id, check_name),
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id)
            )
        """)


def verify_check(business_id, check_name, verified_by):
    if check_name not in CHECKS:
        raise ValueError("Unknown activation check")

    if not verified_by or not verified_by.strip():
        raise ValueError("Verifier required")

    migrate_activation()

    if get_workspace(business_id) is None:
        raise ValueError("Workspace not found")

    with connect() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO pilot_activation_checks
            (business_id, check_name, verified_by)
            VALUES (?, ?, ?)
            """,
            (business_id, check_name, verified_by.strip()),
        )


def activation_status(business_id):
    migrate_activation()

    workspace = get_workspace(business_id)

    if workspace is None:
        raise ValueError("Workspace not found")

    with connect() as db:
        rows = db.execute(
            """
            SELECT check_name
            FROM pilot_activation_checks
            WHERE business_id = ?
            """,
            (business_id,),
        ).fetchall()

    verified = {row["check_name"] for row in rows}
    missing = sorted(set(CHECKS) - verified)

    return ActivationResult(
        business_id=business_id,
        status=workspace["status"],
        missing_checks=missing,
    )


def activate_workspace(business_id):
    migrate_activation()

    with connect() as db:
        workspace = db.execute(
            """
            SELECT status
            FROM pilot_workspaces
            WHERE business_id = ?
            """,
            (business_id,),
        ).fetchone()

        if workspace is None:
            raise ValueError("Workspace not found")

        if workspace["status"] != "pending_verification":
            raise ValueError("Workspace is not pending")

        rows = db.execute(
            """
            SELECT check_name
            FROM pilot_activation_checks
            WHERE business_id = ?
            """,
            (business_id,),
        ).fetchall()

        verified = {row["check_name"] for row in rows}
        missing = sorted(set(CHECKS) - verified)

        if missing:
            raise ValueError(
                "Activation blocked: " + ", ".join(missing)
            )

        cursor = db.execute(
            """
            UPDATE pilot_workspaces
            SET status = 'active',
                activated_at = CURRENT_TIMESTAMP
            WHERE business_id = ?
              AND status = 'pending_verification'
            """,
            (business_id,),
        )

        if cursor.rowcount != 1:
            raise ValueError("Activation state changed")

    return ActivationResult(
        business_id=business_id,
        status="active",
        missing_checks=[],
    )
