from fastapi import FastAPI

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
