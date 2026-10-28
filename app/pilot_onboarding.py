from dataclasses import dataclass, field
from datetime import date, timedelta

PILOT_PRICE = 49
PILOT_DAYS = 14

PLANS = {
    "basic": {"monthly_price": 29, "lead_limit": 50},
    "growth": {"monthly_price": 59, "lead_limit": 200},
}


@dataclass
class PilotApplication:
    business_name: str
    contact_email: str
    plan: str = "basic"
    services: list = field(default_factory=list)


def validate_application(application):
    errors = []

    if not 2 <= len(application.business_name.strip()) <= 120:
        errors.append("invalid_business_name")

    email = application.contact_email.strip()

    if (
        len(email) > 254
        or "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
    ):
        errors.append("invalid_email")

    if application.plan not in PLANS:
        errors.append("invalid_plan")

    if len(application.services) > 20:
        errors.append("too_many_services")

    return errors


def prepare_pilot(application, start_date=None):
    errors = validate_application(application)

    if errors:
        raise ValueError(", ".join(errors))

    start = start_date or date.today()
    end = start + timedelta(days=PILOT_DAYS)

    return {
        "business_name": application.business_name.strip(),
        "contact_email": application.contact_email.strip(),
        "plan": application.plan,
        "services": application.services,
        "pilot_price": PILOT_PRICE,
        "pilot_days": PILOT_DAYS,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "monthly_price_after_pilot": PLANS[
            application.plan
        ]["monthly_price"],
        "monthly_lead_limit": PLANS[
            application.plan
        ]["lead_limit"],
        "status": "pending_verification",
        "payment_confirmed": False,
        "terms_accepted": False,
        "workspace_provisioned": False,
        "checklist": [
            "Confirm business ownership",
            "Agree to service and data-handling terms",
            "Confirm payment",
            "Configure tenant-specific access",
            "Verify lead intake and approval workflow",
            "Run fictional demonstration",
            "Authorize pilot activation",
        ],
    }
