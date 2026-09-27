"""Router de historia: materializar rama -> escenas, y Continue Story."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import ollama_client
from models import Scene, StoryPlan
from storage import (
    branch_path,
    get_project,
    get_story_plan,
    save_story_plan,
    set_node_status,
)

router = APIRouter(prefix="/api/projects/{project_id}/story", tags=["story"])


class MaterializeRequest(BaseModel):
    node_id: str
    scene_count: int = Field(default=6, ge=1, le=12)
    style: str = "anime cinematografico"


class ContinueRequest(BaseModel):
    extra_scenes: int = Field(default=2, ge=1, le=6)
    style: str = "anime cinematografico"


def _require_project(project_id: str) -> None:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")


def _to_scenes(items: list[dict], start_order: int = 1) -> list[Scene]:
    scenes = []
    for i, item in enumerate(items, start=start_order):
        scenes.append(
            Scene(
                scene_id=f"scene-{i:02d}",
                order=i,
                title=item.get("title", f"Escena {i}"),
                purpose=item.get("purpose", ""),
                duration_seconds=item.get("duration_seconds", 8),
                image_prompt=item.get("image_prompt", ""),
                motion_prompt=item.get("motion_prompt", ""),
                narration=item.get("narration", ""),
                subtitle_text=item.get("subtitle_text", "")
                or item.get("narration", ""),
            )
        )
    return scenes


@router.post("/materialize", response_model=StoryPlan)
def api_materialize(project_id: str, payload: MaterializeRequest) -> StoryPlan:
    _require_project(project_id)
    path = branch_path(project_id, payload.node_id)
    if path is None:
        raise HTTPException(status_code=404, detail="node not found")
    try:
        story = ollama_client.generate_story(path, payload.scene_count, payload.style)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    plan = StoryPlan(
        hook=story["hook"],
        summary=story["summary"],
        cliffhanger=story["cliffhanger"],
        scenes=_to_scenes(story["scenes"]),
    )
    set_node_status(project_id, payload.node_id, "selected_for_story")
    return save_story_plan(project_id, plan)


@router.post("/continue", response_model=StoryPlan)
def api_continue_story(project_id: str, payload: ContinueRequest) -> StoryPlan:
    _require_project(project_id)
    plan = get_story_plan(project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="project not found")
    if not plan.scenes:
        raise HTTPException(
            status_code=400, detail="no hay escenas: materializa una rama primero"
        )
    from storage import load_tree

    tree = load_tree(project_id)
    selected = (tree or {}).get("selected_story_node_id")
    path = branch_path(project_id, selected) if selected else None
    if path is None:
        # Sin rama marcada: continuar solo con el contexto de escenas previas.
        path = [{"title": plan.summary, "summary": plan.summary, "conflict": ""}]
    try:
        story = ollama_client.generate_more_scenes(
            path,
            [s.model_dump() for s in plan.scenes],
            payload.extra_scenes,
            payload.style,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    plan.scenes.extend(_to_scenes(story["scenes"], start_order=len(plan.scenes) + 1))
    if story.get("cliffhanger"):
        plan.cliffhanger = story["cliffhanger"]
    return save_story_plan(project_id, plan)
