"""Router de proyectos: crear, listar, obtener, ver story plan."""
from fastapi import APIRouter, HTTPException

from models import Project, ProjectCreate, StoryPlan
from storage import create_project, get_project, get_story_plan, list_projects

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=Project)
def api_create_project(payload: ProjectCreate) -> Project:
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    return create_project(payload)


@router.get("", response_model=list[Project])
def api_list_projects() -> list[Project]:
    return list_projects()


@router.get("/{project_id}", response_model=Project)
def api_get_project(project_id: str) -> Project:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("/{project_id}/story-plan", response_model=StoryPlan)
def api_get_story_plan(project_id: str) -> StoryPlan:
    plan = get_story_plan(project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="project not found")
    return plan
