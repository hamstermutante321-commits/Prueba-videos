"""StoryForge Local Studio - Backend base (Phase 2)."""
from fastapi import FastAPI
from pydantic import BaseModel

from routers.projects import router as projects_router

app = FastAPI(title="StoryForge Local Studio", version="0.2.0")
app.include_router(projects_router)


class HealthResponse(BaseModel):
    status: str
    app: str
    phase: str


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app="storyforge-local-studio", phase="phase-2-backend")
