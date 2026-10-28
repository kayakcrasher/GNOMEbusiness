from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import connect
from app.appointments.api import migrate

router = APIRouter(prefix="/api", tags=["Conversions"])


class ConversionRequest(BaseModel):
    business_id: int = Field(gt=0)
    lead_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    notes: str = Field(default="", max_length=5000)


@router.post("/conversions/book", status_code=201)
def book_lead(data: ConversionRequest):
    migrate()

    if data.starts_at.tzinfo is None:
        raise HTTPException(
            422, "Appointment requires a timezone"
        )

    with connect() as db:
        lead = db.execute(
            """
            SELECT id, company, status
            FROM leads
            WHERE id = ? AND business_id = ?
            """,
            (data.lead_id, data.business_id),
        ).fetchone()

        if lead is None:
            raise HTTPException(
                404, "Lead not found in this business"
            )

        if lead["status"] == "closed":
            raise HTTPException(
                409, "Closed leads cannot be booked"
            )

        cursor = db.execute(
            """
            INSERT INTO appointments
            (business_id, lead_id, title, starts_at, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data.business_id,
                data.lead_id,
                data.title,
                data.starts_at.isoformat(),
                data.notes,
            ),
        )

        db.execute(
            """
            UPDATE leads
            SET status = 'booked'
            WHERE id = ? AND business_id = ?
            """,
            (data.lead_id, data.business_id),
        )

        appointment_id = cursor.lastrowid

    return {
        "appointment_id": appointment_id,
        "lead_id": data.lead_id,
        "lead_status": "booked",
        "appointment_status": "scheduled",
    }
