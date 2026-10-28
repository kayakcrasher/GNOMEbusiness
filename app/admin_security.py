import hashlib
import secrets

from fastapi import HTTPException

from app.database import connect, initialize


ADMIN_PERMISSIONS = {
    "customers:activate",
    "credentials:issue",
    "credentials:revoke",
    "customers:read",
}


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def migrate():
    initialize()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS admin_credentials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                permissions TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                revoked_at TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS admin_security_events (
                id INTEGER PRIMARY KEY,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id)
                    REFERENCES admin_credentials(id)
            )
        """)


def bootstrap_admin(name, permissions):
    """
    Trusted local bootstrap only.
    Never expose through an HTTP endpoint.
    """
    if not name or not name.strip():
        raise ValueError("Administrator name required")

    requested = set(permissions)

    if not requested or not requested <= ADMIN_PERMISSIONS:
        raise ValueError("Invalid permissions")

    migrate()

    with connect() as db:
        existing = db.execute(
            """
            SELECT COUNT(*) FROM admin_credentials
            WHERE revoked_at IS NULL
            """
        ).fetchone()[0]

        if existing:
            raise ValueError(
                "Active administrator already exists"
            )

        token = "gnadmin_" + secrets.token_urlsafe(32)

        cursor = db.execute(
            """
            INSERT INTO admin_credentials
            (name, token_hash, permissions)
            VALUES (?, ?, ?)
            """,
            (
                name.strip(),
                digest(token),
                ",".join(sorted(requested)),
            ),
        )

    return {
        "admin_id": cursor.lastrowid,
        "token": token,
    }


def authorize_admin(token, permission):
    if permission not in ADMIN_PERMISSIONS:
        raise ValueError("Unknown admin permission")

    migrate()

    if not token or not token.startswith("gnadmin_"):
        raise HTTPException(401, "Administrator token required")

    with connect() as db:
        admin = db.execute(
            """
            SELECT id, name, permissions
            FROM admin_credentials
            WHERE token_hash = ?
              AND revoked_at IS NULL
            """,
            (digest(token),),
        ).fetchone()

        if admin is None:
            raise HTTPException(401, "Invalid administrator token")

        allowed = permission in admin["permissions"].split(",")

        db.execute(
            """
            INSERT INTO admin_security_events
            (admin_id, action, result)
            VALUES (?, ?, ?)
            """,
            (
                admin["id"],
                permission,
                "allowed" if allowed else "denied",
            ),
        )

    if not allowed:
        raise HTTPException(403, "Administrator permission denied")

    return {
        "admin_id": admin["id"],
        "name": admin["name"],
    }
