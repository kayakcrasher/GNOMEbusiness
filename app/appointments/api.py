from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import connect, initialize

router = APIRouter(prefix="/api", tags=["GNOMEbook"])


def migrate():
    initialize()
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                lead_id INTEGER,
                title TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'scheduled',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id),
                FOREIGN KEY (lead_id)
                    REFERENCES leads(id)
            )
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_business
            ON appointments(business_id, starts_at)
        """)


class AppointmentCreate(BaseModel):
    business_id: int
    lead_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    notes: str = Field(default="", max_length=5000)


class AppointmentUpdate(BaseModel):
    status: Literal["scheduled", "completed", "cancelled"]


@router.post("/appointments", status_code=201)
def create_appointment(data: AppointmentCreate):
    migrate()

    if data.starts_at.tzinfo is None:
        raise HTTPException(
            422, "Appointment time must include a timezone"
        )

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (data.business_id,),
        ).fetchone()

        if not business:
            raise HTTPException(404, "Business not found")

        if data.lead_id is not None:
            lead = db.execute(
                """
                SELECT id FROM leads
                WHERE id = ? AND business_id = ?
                """,
                (data.lead_id, data.business_id),
            ).fetchone()

            if not lead:
                raise HTTPException(
                    404, "Lead not found in this business"
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
        appointment_id = cursor.lastrowid

    return {"id": appointment_id, "status": "scheduled"}


@router.get("/businesses/{business_id}/appointments")
def list_appointments(business_id: int):
    migrate()

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if not business:
            raise HTTPException(404, "Business not found")

        rows = db.execute(
            """
            SELECT * FROM appointments
            WHERE business_id = ?
            ORDER BY starts_at ASC
            """,
            (business_id,),
        ).fetchall()

    return {"appointments": [dict(row) for row in rows]}


@router.patch("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: int,
    change: AppointmentUpdate,
):
    migrate()

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE appointments SET status = ?
            WHERE id = ?
            """,
            (change.status, appointment_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Appointment not found")

    return {
        "id": appointment_id,
        "status": change.status,
    }
