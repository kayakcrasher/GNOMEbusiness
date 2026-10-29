from fastapi import FastAPI
from app.production_guard import validate_production_config

validate_production_config()

app = FastAPI(
    title="GNOMEbusiness",
    version="0.1.0",
)

@app.get("/api/health")
def health():
    return {
        "status": "operational",
        "platform": "GNOMEbusiness",
    }

@app.get("/api/modules")
def modules():
    return {
        "modules": [
            "GNOMEleads",
            "GNOMEbook",
            "GNOMEreach",
        ]
    }

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND = BASE_DIR / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND),
    name="static",
)

@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND / "index.html")

from app.leads.api import router as leads_router

app.include_router(leads_router)

from app.dashboard import router as dashboard_router

app.include_router(dashboard_router)

from app.followups import router as followups_router

app.include_router(followups_router)

from app.tasks import router as tasks_router

app.include_router(tasks_router)

from app.appointments.api import router as appointments_router
app.include_router(appointments_router)

from app.outreach.api import router as outreach_router
app.include_router(outreach_router)

from app.appointments.conversion import router as conversion_router
app.include_router(conversion_router)

from app.reporting import router as reporting_router
app.include_router(reporting_router)

from app.security import router as security_router
app.include_router(security_router)

from app.tenant_guard import TenantGuard
app.add_middleware(TenantGuard)

from app.auth import router as auth_router
app.include_router(auth_router)


@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(FRONTEND / "login.html")

from app.agent_gateway import router as agent_router
app.include_router(agent_router)

from app.approvals import router as approvals_router
app.include_router(approvals_router)


@app.get("/agents", include_in_schema=False)
def agent_control_center():
    return FileResponse(FRONTEND / "agents.html")

from app.agent_workstation import router as workstation_router
app.include_router(workstation_router)


from app.muse_connector import router as muse_connector_router
app.include_router(muse_connector_router)


from app.connector_management import router as connector_management_router
app.include_router(connector_management_router)
