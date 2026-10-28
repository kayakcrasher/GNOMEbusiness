from fastapi import HTTPException

from app.database import connect
from app.workspace_provisioning import migrate


def require_active_workspace(business_id):
    migrate()

    with connect() as db:
        row = db.execute(
            """
            SELECT status
            FROM pilot_workspaces
            WHERE business_id = ?
            """,
            (business_id,),
        ).fetchone()

    if row is None:
        # Legacy development businesses are not pilot workspaces.
        return business_id

    if row["status"] != "active":
        raise HTTPException(
            status_code=403,
            detail="Customer workspace is not active",
        )

    return business_id
