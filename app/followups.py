from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import connect, initialize

router = APIRouter(prefix="/api", tags=["Follow-ups"])


def migrate():
    initialize()

    with connect() as db:
        columns = {
            row["name"]
            for row in db.execute(
                "PRAGMA table_info(leads)"
            )
        }

        if "follow_up" not in columns:
            db.execute(
                "ALTER TABLE leads ADD COLUMN follow_up TEXT"
            )

        if "notes" not in columns:
            db.execute(
                "ALTER TABLE leads ADD COLUMN notes TEXT"
            )


class FollowUpUpdate(BaseModel):
    follow_up: date | None = None
    notes: str = Field(default="", max_length=5000)


@router.patch("/leads/{lead_id}/followup")
def update_followup(lead_id: int, change: FollowUpUpdate):
    migrate()

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE leads
            SET follow_up = ?, notes = ?
            WHERE id = ?
            """,
            (
                change.follow_up.isoformat()
                if change.follow_up else None,
                change.notes,
                lead_id,
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Lead not found")

    return {
        "id": lead_id,
        "follow_up": change.follow_up,
        "notes": change.notes,
    }


@router.get("/businesses/{business_id}/followups")
def list_followups(business_id: int):
    migrate()

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if business is None:
            raise HTTPException(404, "Business not found")

        rows = db.execute(
            """
            SELECT id, company, contact,
                   status, follow_up, notes
            FROM leads
            WHERE business_id = ?
              AND follow_up IS NOT NULL
              AND status != 'closed'
            ORDER BY follow_up ASC, id DESC
            """,
            (business_id,),
        ).fetchall()

    return {
        "followups": [dict(row) for row in rows]
    }
