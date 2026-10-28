from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import connect, initialize

router = APIRouter(prefix="/api", tags=["GNOMEreach"])

MessageStatus = Literal["draft", "ready", "sent"]


def migrate():
    initialize()
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS outreach (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                lead_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id),
                FOREIGN KEY (lead_id)
                    REFERENCES leads(id)
            )
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_outreach_business
            ON outreach(business_id, lead_id)
        """)


class MessageCreate(BaseModel):
    business_id: int = Field(gt=0)
    lead_id: int = Field(gt=0)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


class MessageUpdate(BaseModel):
    status: MessageStatus


@router.post("/outreach", status_code=201)
def create_message(data: MessageCreate):
    migrate()

    with connect() as db:
        lead = db.execute(
            """
            SELECT id FROM leads
            WHERE id = ? AND business_id = ?
            """,
            (data.lead_id, data.business_id),
        ).fetchone()

        if lead is None:
            raise HTTPException(
                404, "Lead not found in this business"
            )

        cursor = db.execute(
            """
            INSERT INTO outreach
            (business_id, lead_id, subject, body)
            VALUES (?, ?, ?, ?)
            """,
            (
                data.business_id,
                data.lead_id,
                data.subject,
                data.body,
            ),
        )

        message_id = cursor.lastrowid

    return {"id": message_id, "status": "draft"}


@router.get("/businesses/{business_id}/outreach")
def list_messages(business_id: int):
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
            SELECT o.*, l.company, l.contact, l.email
            FROM outreach o
            JOIN leads l ON l.id = o.lead_id
            WHERE o.business_id = ?
            ORDER BY o.id DESC
            """,
            (business_id,),
        ).fetchall()

    return {"messages": [dict(row) for row in rows]}


@router.patch("/outreach/{message_id}")
def update_message(message_id: int, change: MessageUpdate):
    migrate()

    with connect() as db:
        cursor = db.execute(
            """
            UPDATE outreach SET status = ?
            WHERE id = ?
            """,
            (change.status, message_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Message not found")

    return {"id": message_id, "status": change.status}
