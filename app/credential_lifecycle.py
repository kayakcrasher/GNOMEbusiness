from app.database import connect
from app.security import (
    create_key,
    hash_key,
    migrate as owner_migrate,
)
from app.agent_gateway import (
    provision_agent,
    migrate as agent_migrate,
    SCOPES,
)
from app.workspace_provisioning import get_workspace
from app.workspace_access import require_active_workspace


def migrate():
    owner_migrate()
    agent_migrate()

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS credential_events (
                id INTEGER PRIMARY KEY,
                business_id INTEGER NOT NULL,
                credential_type TEXT NOT NULL,
                credential_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                operator TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id)
                    REFERENCES businesses(id)
            )
        """)


def validate_operator(operator):
    if not operator or not operator.strip():
        raise ValueError("Operator required")
    return operator.strip()


def require_customer_active(business_id):
    workspace = get_workspace(business_id)

    if workspace is None:
        raise ValueError("Customer pilot workspace required")

    require_active_workspace(business_id)


def record_event(
    db, business_id, credential_type,
    credential_id, action, operator
):
    db.execute(
        """
        INSERT INTO credential_events
        (business_id, credential_type, credential_id,
         action, operator)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            business_id,
            credential_type,
            credential_id,
            action,
            operator,
        ),
    )


def issue_owner_key(business_id, operator):
    import secrets

    operator = validate_operator(operator)
    migrate()
    require_customer_active(business_id)

    key = "gnb_" + secrets.token_urlsafe(32)

    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO api_keys (business_id, key_hash)
            SELECT id, ? FROM businesses WHERE id = ?
            """,
            (hash_key(key), business_id),
        )

        if cursor.rowcount != 1:
            raise ValueError("Business not found")

        record_event(
            db, business_id, "owner",
            cursor.lastrowid, "issued", operator,
        )

    return key


def issue_agent_token(
    business_id, name, scopes, operator
):
    import secrets
    from app.agent_gateway import digest

    operator = validate_operator(operator)
    requested = set(scopes)

    if not requested or not requested <= SCOPES:
        raise ValueError("Invalid agent scopes")

    if not name or not name.strip():
        raise ValueError("Agent name required")

    migrate()
    require_customer_active(business_id)

    token = "gna_" + secrets.token_urlsafe(32)

    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO agent_credentials
            (business_id, name, token_hash, scopes)
            SELECT id, ?, ?, ?
            FROM businesses WHERE id = ?
            """,
            (
                name.strip(),
                digest(token),
                ",".join(sorted(requested)),
                business_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError("Business not found")

        agent_id = cursor.lastrowid

        record_event(
            db, business_id, "agent",
            agent_id, "issued", operator,
        )

    return {
        "agent_id": agent_id,
        "token": token,
    }


def revoke_credential(
    business_id, credential_type,
    credential_id, operator
):
    operator = validate_operator(operator)

    if credential_type not in {"owner", "agent"}:
        raise ValueError("Invalid credential type")

    migrate()

    table = (
        "api_keys"
        if credential_type == "owner"
        else "agent_credentials"
    )

    with connect() as db:
        cursor = db.execute(
            f"""
            UPDATE {table}
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND business_id = ?
              AND revoked_at IS NULL
            """,
            (credential_id, business_id),
        )

        if cursor.rowcount != 1:
            return False

        record_event(
            db, business_id, credential_type,
            credential_id, "revoked", operator,
        )

    return True


def credential_inventory(business_id):
    migrate()

    with connect() as db:
        owners = db.execute(
            """
            SELECT id, created_at, revoked_at
            FROM api_keys
            WHERE business_id = ?
            ORDER BY id
            """,
            (business_id,),
        ).fetchall()

        agents = db.execute(
            """
            SELECT id, name, scopes,
                   created_at, revoked_at
            FROM agent_credentials
            WHERE business_id = ?
            ORDER BY id
            """,
            (business_id,),
        ).fetchall()

    return {
        "owners": [dict(row) for row in owners],
        "agents": [dict(row) for row in agents],
    }
