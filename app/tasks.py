from datetime import date

from fastapi import APIRouter, HTTPException

from app.database import connect
from app.followups import migrate

router = APIRouter(prefix="/api", tags=["Tasks"])


@router.get("/businesses/{business_id}/tasks")
def get_tasks(business_id: int):
    migrate()
    today = date.today().isoformat()

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if business is None:
            raise HTTPException(404, "Business not found")

        rows = db.execute(
            """
            SELECT id, company, contact, status,
                   follow_up, notes
            FROM leads
            WHERE business_id = ?
              AND follow_up IS NOT NULL
              AND status != 'closed'
            ORDER BY follow_up ASC, id ASC
            """,
            (business_id,),
        ).fetchall()

    tasks = []
    summary = {
        "overdue": 0,
        "today": 0,
        "upcoming": 0,
    }

    for row in rows:
        task = dict(row)

        if task["follow_up"] < today:
            due = "overdue"
        elif task["follow_up"] == today:
            due = "today"
        else:
            due = "upcoming"

        task["due"] = due
        summary[due] += 1
        tasks.append(task)

    return {
        "summary": summary,
        "tasks": tasks,
    }


@router.patch("/leads/{lead_id}/complete-followup")
def complete_followup(lead_id: int):
    migrate()

    with connect() as db:
        lead = db.execute(
            """
            SELECT id, follow_up
            FROM leads
            WHERE id = ?
            """,
            (lead_id,),
        ).fetchone()

        if lead is None:
            raise HTTPException(404, "Lead not found")

        if lead["follow_up"] is None:
            raise HTTPException(
                409, "No active follow-up to complete"
            )

        db.execute(
            """
            UPDATE leads
            SET follow_up = NULL
            WHERE id = ?
            """,
            (lead_id,),
        )

    return {
        "id": lead_id,
        "completed": True,
    }
