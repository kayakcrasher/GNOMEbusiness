from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import connect, initialize

router = APIRouter(prefix="/api", tags=["Leads"])

LeadStatus = Literal[
    "new", "contacted", "interested",
    "booked", "closed"
]


class LeadCreate(BaseModel):
    business_id: int = Field(gt=0)
    company: str = Field(min_length=1, max_length=200)
    contact: str = ""
    email: str = ""


class LeadUpdate(BaseModel):
    status: LeadStatus


@router.post("/leads", status_code=201)
def create_lead(lead: LeadCreate):
    initialize()

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (lead.business_id,)
        ).fetchone()

        if business is None:
            raise HTTPException(
                status_code=404,
                detail="Business not found"
            )

        cursor = db.execute(
            """
            INSERT INTO leads
            (business_id, company, contact, email)
            VALUES (?, ?, ?, ?)
            """,
            (
                lead.business_id,
                lead.company,
                lead.contact,
                lead.email,
            )
        )

        lead_id = cursor.lastrowid

    return {"id": lead_id, "status": "new"}


@router.get("/businesses/{business_id}/leads")
def list_leads(business_id: int):
    initialize()

    with connect() as db:
        rows = db.execute(
            """
            SELECT * FROM leads
            WHERE business_id = ?
            ORDER BY id DESC
            """,
            (business_id,)
        ).fetchall()

    return {"leads": [dict(row) for row in rows]}


@router.get("/leads/{lead_id}")
def get_lead(lead_id: int):
    initialize()

    with connect() as db:
        row = db.execute(
            "SELECT * FROM leads WHERE id = ?",
            (lead_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Lead not found")

    return dict(row)


@router.patch("/leads/{lead_id}")
def update_lead(lead_id: int, change: LeadUpdate):
    initialize()

    with connect() as db:
        cursor = db.execute(
            "UPDATE leads SET status = ? WHERE id = ?",
            (change.status, lead_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Lead not found")

    return {
        "id": lead_id,
        "status": change.status,
    }
