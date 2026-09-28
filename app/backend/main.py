"""StoryForge Local Studio - Backend base (Phase 2)."""
from fastapi import FastAPI
from pydantic import BaseModel

from routers.ideas import router as ideas_router
from routers.images import router as images_router
from routers.jobs import router as jobs_router
from routers.projects import router as projects_router
from routers.render import router as render_router
from routers.story import router as story_router
from routers.subs import router as subs_router
from routers.system import router as system_router
from routers.videos import router as videos_router
from routers.voice import router as voice_router

app = FastAPI(title="StoryForge Local Studio", version="0.2.0")
app.include_router(projects_router)
app.include_router(ideas_router)
app.include_router(jobs_router)
app.include_router(story_router)
app.include_router(images_router)
app.include_router(videos_router)
app.include_router(voice_router)
app.include_router(subs_router)
app.include_router(render_router)
app.include_router(system_router)


class HealthResponse(BaseModel):
    status: str
    app: str
    phase: str


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app="storyforge-local-studio", phase="phase-2-backend")
