from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import connect, initialize

router = APIRouter(
    prefix="/api",
    tags=["Dashboard"],
)


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


@router.post("/businesses", status_code=201)
def create_business(business: BusinessCreate):
    initialize()

    with connect() as db:
        cursor = db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            (business.name,),
        )

        business_id = cursor.lastrowid

    return {
        "id": business_id,
        "name": business.name,
    }


@router.get("/businesses/{business_id}/dashboard")
def dashboard_stats(business_id: int):
    initialize()

    with connect() as db:
        business = db.execute(
            "SELECT * FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if business is None:
            raise HTTPException(
                status_code=404,
                detail="Business not found",
            )

        rows = db.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM leads
            WHERE business_id = ?
            GROUP BY status
            """,
            (business_id,),
        ).fetchall()

        recent = db.execute(
            """
            SELECT id, company, contact, status
            FROM leads
            WHERE business_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (business_id,),
        ).fetchall()

    counts = {
        "new": 0,
        "contacted": 0,
        "interested": 0,
        "booked": 0,
        "closed": 0,
    }

    for row in rows:
        counts[row["status"]] = row["total"]

    return {
        "business": dict(business),
        "total_leads": sum(counts.values()),
        "pipeline": counts,
        "recent_leads": [
            dict(row) for row in recent
        ],
    }
