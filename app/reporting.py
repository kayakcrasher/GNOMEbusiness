from fastapi import APIRouter, HTTPException

from app.database import connect
from app.appointments.api import migrate as migrate_bookings
from app.outreach.api import migrate as migrate_outreach

router = APIRouter(prefix="/api", tags=["Reporting"])


@router.get("/businesses/{business_id}/report")
def business_report(business_id: int):
    migrate_bookings()
    migrate_outreach()

    with connect() as db:
        business = db.execute(
            "SELECT id, name FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if business is None:
            raise HTTPException(404, "Business not found")

        total_leads = db.execute(
            "SELECT COUNT(*) FROM leads WHERE business_id = ?",
            (business_id,),
        ).fetchone()[0]

        contacted = db.execute(
            """
            SELECT COUNT(DISTINCT lead_id)
            FROM outreach
            WHERE business_id = ? AND status = 'sent'
            """,
            (business_id,),
        ).fetchone()[0]

        sent_messages = db.execute(
            """
            SELECT COUNT(*) FROM outreach
            WHERE business_id = ? AND status = 'sent'
            """,
            (business_id,),
        ).fetchone()[0]

        appointments = db.execute(
            """
            SELECT COUNT(*) FROM appointments
            WHERE business_id = ? AND status != 'cancelled'
            """,
            (business_id,),
        ).fetchone()[0]

        booked_leads = db.execute(
            """
            SELECT COUNT(DISTINCT lead_id)
            FROM appointments
            WHERE business_id = ?
              AND lead_id IS NOT NULL
              AND status != 'cancelled'
            """,
            (business_id,),
        ).fetchone()[0]

        completed = db.execute(
            """
            SELECT COUNT(*) FROM appointments
            WHERE business_id = ? AND status = 'completed'
            """,
            (business_id,),
        ).fetchone()[0]

    conversion_rate = (
        round(booked_leads / total_leads * 100, 1)
        if total_leads else 0.0
    )

    return {
        "business": dict(business),
        "total_leads": total_leads,
        "contacted_prospects": contacted,
        "sent_messages": sent_messages,
        "appointments": appointments,
        "booked_leads": booked_leads,
        "completed_appointments": completed,
        "conversion_rate": conversion_rate,
    }
