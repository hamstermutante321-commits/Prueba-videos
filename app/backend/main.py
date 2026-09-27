"""StoryForge Local Studio - Backend base (Phase 1/2)."""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="StoryForge Local Studio", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    app: str
    phase: str


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app="storyforge-local-studio", phase="phase-1-skeleton")


@app.get("/api/projects")
def list_projects() -> dict:
    # Phase 4+ implementará persistencia real en projects/
    return {"projects": []}
