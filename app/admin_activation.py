"""Authenticated administrative operations for pilot activation."""

from app.admin_security import authorize_admin
from app.pilot_activation import (
    CHECKS,
    verify_check,
    activate_workspace,
    activation_status,
)


def verify_customer_check(admin_token, business_id, check_name):
    admin = authorize_admin(admin_token, "customers:activate")

    if check_name not in CHECKS:
        raise ValueError("Unknown activation check")

    verify_check(
        business_id,
        check_name,
        f"admin:{admin['admin_id']}",
    )

    return activation_status(business_id)


def activate_customer(admin_token, business_id):
    authorize_admin(admin_token, "customers:activate")
    return activate_workspace(business_id)


def inspect_customer_activation(admin_token, business_id):
    authorize_admin(admin_token, "customers:read")
    return activation_status(business_id)
