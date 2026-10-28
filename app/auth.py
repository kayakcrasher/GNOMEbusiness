import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Response, Cookie
from pydantic import BaseModel, Field

from app.database import connect, initialize

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

SESSION_DAYS = 7
COOKIE_NAME = "gnome_session"


def migrate():
    initialize()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
            )
        """)


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=16384,
        r=8,
        p=1,
    )
    return salt.hex() + ":" + digest.hex()


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)

        actual = hashlib.scrypt(
            password.encode(),
            salt=salt,
            n=16384,
            r=8,
            p=1,
        )

        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_user(business_id, username, password):
    migrate()

    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")

    with connect() as db:
        business = db.execute(
            "SELECT id FROM businesses WHERE id = ?",
            (business_id,),
        ).fetchone()

        if business is None:
            raise ValueError("Business not found")

        cursor = db.execute(
            """
            INSERT INTO users
            (business_id, username, password_hash)
            VALUES (?, ?, ?)
            """,
            (
                business_id,
                username,
                hash_password(password),
            ),
        )

        return cursor.lastrowid


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1)


@router.post("/login")
def login(data: LoginRequest, response: Response):
    migrate()

    with connect() as db:
        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (data.username,),
        ).fetchone()

        if user is None or not verify_password(
            data.password, user["password_hash"]
        ):
            raise HTTPException(401, "Invalid credentials")

        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(
            days=SESSION_DAYS
        )

        db.execute(
            """
            INSERT INTO sessions
            (token_hash, user_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (
                token_hash(token),
                user["id"],
                expires.isoformat(),
            ),
        )

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=SESSION_DAYS * 86400,
        path="/",
    )

    return {
        "authenticated": True,
        "business_id": user["business_id"],
    }


def session_user(token):
    if not token:
        raise HTTPException(401, "Login required")

    migrate()

    with connect() as db:
        row = db.execute(
            """
            SELECT u.id, u.username, u.business_id,
                   s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash(token),),
        ).fetchone()

    if row is None:
        raise HTTPException(401, "Invalid session")

    expires = datetime.fromisoformat(row["expires_at"])

    if expires <= datetime.now(timezone.utc):
        raise HTTPException(401, "Session expired")

    return {
        "id": row["id"],
        "username": row["username"],
        "business_id": row["business_id"],
    }


@router.get("/me")
def current_user(
    gnome_session: str | None = Cookie(default=None),
):
    return session_user(gnome_session)


@router.post("/logout")
def logout(
    response: Response,
    gnome_session: str | None = Cookie(default=None),
):
    if gnome_session:
        migrate()

        with connect() as db:
            db.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (token_hash(gnome_session),),
            )

    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )

    return {"authenticated": False}
