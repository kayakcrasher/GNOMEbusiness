from fastapi import APIRouter

router = APIRouter(
    prefix="/api/connectors",
    tags=["External Agent Connectors"],
)


@router.get("/muse")
def muse_connector_manifest():
    return {
        "name": "GNOMEbusiness",
        "provider": "muse",
        "version": "0.1",
        "mode": "external_agent_client",
        "authentication": {
            "type": "bearer",
            "provisioning": "trusted_server_only",
        },
        "capabilities": [
            {
                "name": "list_leads",
                "method": "GET",
                "path": "/api/agents/leads",
                "scope": "leads:read",
            },
            {
                "name": "list_appointments",
                "method": "GET",
                "path": "/api/agents/appointments",
                "scope": "appointments:read",
            },
            {
                "name": "create_job",
                "method": "POST",
                "path": "/api/workstation/jobs",
                "scope": "jobs:work",
                "allowed_kinds": [
                    "lead:analyze",
                    "lead:process",
                    "outreach:draft",
                    "appointment:research",
                ],
            },
            {
                "name": "list_jobs",
                "method": "GET",
                "path": "/api/workstation/jobs",
                "scope": "jobs:work",
            },
        ],
        "safety": {
            "human_approval_required": True,
            "external_actions_enabled": False,
        },
    }
