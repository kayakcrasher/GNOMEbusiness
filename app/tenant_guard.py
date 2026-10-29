import os
import re

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import connect
from app.security import authenticate

BUSINESS_PATH = re.compile(
    r"^/api/businesses/(\d+)(?:/|$)"
)

RECORD_PATH = re.compile(
    r"^/api/(leads|appointments|outreach)/(\d+)"
    r"(?:/|$)"
)

PUBLIC_PATHS = {
    "/api/health",
    "/api/modules",
}


def record_owner(kind, record_id):
    table = {
        "leads": "leads",
        "appointments": "appointments",
        "outreach": "outreach",
    }[kind]

    with connect() as db:
        row = db.execute(
            f"SELECT business_id FROM {table} WHERE id = ?",
            (record_id,),
        ).fetchone()

    return row["business_id"] if row else None


class TenantGuard(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        environment = os.getenv(
            "GNOME_ENV", "production"
        ).strip().lower()

        auth_setting = os.getenv(
            "GNOME_ENFORCE_AUTH", "1"
        )

        if (
            environment in {"development", "test"}
            and auth_setting == "0"
        ):
            return await call_next(request)

        path = request.url.path

        if not path.startswith("/api/"):
            return await call_next(request)

        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Agent routes authenticate bearer credentials
        # through their own scoped gateway.
        # Never grant agent tokens owner-level access.
        if path.startswith("/api/agents/"):
            return await call_next(request)

        # Connector management uses authenticated owner sessions.
        # Its handlers validate the session and tenant ownership.
        if (
            path == "/api/connectors/manage"
            or path.startswith("/api/connectors/manage/")
        ):
            return await call_next(request)

        # Customer job routes validate owner sessions
        # and enforce tenant ownership in their handlers.
        if (
            path == "/api/customer/jobs"
            or path.startswith("/api/customer/jobs/")
        ):
            return await call_next(request)

        # Read-only operations use authenticated owner sessions.
        if path == "/api/customer/operations":
            return await call_next(request)

        # Login is public; the handler validates credentials.
        if path == "/api/auth/login" and request.method == "POST":
            return await call_next(request)

        # Workstation endpoints validate scoped agent tokens.
        if path.startswith("/api/workstation/"):
            return await call_next(request)

        if path == "/api/workstation/jobs":
            return await call_next(request)

        # Only proposal submission uses agent credentials.
        # Approval review and decisions remain owner-only.
        if (
            path == "/api/approvals/proposals"
            and request.method == "POST"
        ):
            return await call_next(request)

        # Workspace creation is not a public signup endpoint.
        if path == "/api/businesses":
            return JSONResponse(
                {"detail": "Admin provisioning required"},
                status_code=403,
            )

        try:
            business_id = authenticate(
                request.headers.get("X-API-Key")
            )
        except HTTPException as error:
            return JSONResponse(
                {"detail": error.detail},
                status_code=error.status_code,
            )

        match = BUSINESS_PATH.match(path)

        if match:
            requested_id = int(match.group(1))

            if requested_id != business_id:
                return JSONResponse(
                    {"detail": "Business access denied"},
                    status_code=403,
                )

        match = RECORD_PATH.match(path)

        if match:
            kind, record_id = match.groups()

            owner = record_owner(kind, int(record_id))

            if owner is None:
                return JSONResponse(
                    {"detail": "Record not found"},
                    status_code=404,
                )

            if owner != business_id:
                return JSONResponse(
                    {"detail": "Record access denied"},
                    status_code=403,
                )

        # Check business ownership of JSON request bodies.
        if request.method in {"POST", "PUT", "PATCH"}:
            if path in {
                "/api/leads",
                "/api/appointments",
                "/api/outreach",
                "/api/conversions/book",
            }:
                try:
                    data = await request.json()
                except (ValueError, UnicodeError):
                    return JSONResponse(
                        {"detail": "Invalid JSON"},
                        status_code=400,
                    )

                if not isinstance(data, dict):
                    return JSONResponse(
                        {"detail": "JSON object required"},
                        status_code=400,
                    )

                if type(data.get("business_id")) is not int:
                    return JSONResponse(
                        {"detail": "Business ID required"},
                        status_code=422,
                    )

                if data["business_id"] != business_id:
                    return JSONResponse(
                        {"detail": "Business access denied"},
                        status_code=403,
                    )

        return await call_next(request)
