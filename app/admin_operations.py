from app.admin_security import authorize_admin
from app.credential_lifecycle import (
    issue_owner_key,
    issue_agent_token,
    revoke_credential,
    credential_inventory,
)


def issue_customer_owner_key(admin_token, business_id):
    admin = authorize_admin(
        admin_token, "credentials:issue"
    )

    return issue_owner_key(
        business_id, admin["name"]
    )


def issue_customer_agent_token(
    admin_token, business_id, name, scopes
):
    admin = authorize_admin(
        admin_token, "credentials:issue"
    )

    return issue_agent_token(
        business_id,
        name,
        scopes,
        admin["name"],
    )


def revoke_customer_credential(
    admin_token, business_id,
    credential_type, credential_id
):
    admin = authorize_admin(
        admin_token, "credentials:revoke"
    )

    return revoke_credential(
        business_id,
        credential_type,
        credential_id,
        admin["name"],
    )


def inspect_customer_credentials(
    admin_token, business_id
):
    authorize_admin(
        admin_token, "customers:read"
    )

    return credential_inventory(business_id)
