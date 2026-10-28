import hashlib
import secrets

from fastapi import APIRouter, Header, HTTPException

from app.database import connect, initialize
from app.reporting import business_report

router = APIRouter(prefix="/api", tags=["Security"])


def migrate():
    initialize()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                revoked_at TEXT,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id)
            )
        """)


def hash_key(key):
    return hashlib.sha256(key.encode()).hexdigest()


def create_key(business_id):
    migrate()

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if business is None:
            raise ValueError("Business not found")

        key = "gnb_" + secrets.token_urlsafe(32)

        db.execute(
            """
            INSERT INTO api_keys (business_id, key_hash)
            VALUES (?, ?)
            """,
            (business_id, hash_key(key)),
        )

    return key


def authenticate(key):
    migrate()

    if not key or not key.startswith("gnb_"):
        raise HTTPException(401, "Valid API key required")

    with connect() as db:
        row = db.execute(
            """
            SELECT business_id
            FROM api_keys
            WHERE key_hash = ?
              AND revoked_at IS NULL
            """,
            (hash_key(key),),
        ).fetchone()

    if row is None:
        raise HTTPException(401, "Invalid API key")

    return row["business_id"]


@router.get("/secure/report")
def secure_report(x_api_key: str | None = Header(default=None)):
    business_id = authenticate(x_api_key)
    return business_report(business_id)
