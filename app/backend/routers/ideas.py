"""Router de ideas: generar ideas raíz, subideas, ver árbol, cambiar estado."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import ollama_client
from models import IdeaNode
from storage import (
    add_nodes,
    branch_path,
    get_project,
    load_tree,
    set_node_status,
)

router = APIRouter(prefix="/api/projects/{project_id}/ideas", tags=["ideas"])


class RootIdeasRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=2000)
    style: str = "anime cinematografico"
    count: int = Field(default=4, ge=1, le=8)


class ChildrenRequest(BaseModel):
    count: int = Field(default=4, ge=1, le=8)


class StatusRequest(BaseModel):
    status: str


VALID_STATUSES = {
    "pending",
    "active",
    "favorite",
    "archived",
    "discarded",
    "selected_for_story",
}


def _require_project(project_id: str) -> None:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")


@router.get("")
def api_get_tree(project_id: str) -> dict:
    _require_project(project_id)
    tree = load_tree(project_id)
    if tree is None:
        raise HTTPException(status_code=404, detail="project not found")
    return tree


@router.post("/root")
def api_generate_root_ideas(project_id: str, payload: RootIdeasRequest) -> dict:
    _require_project(project_id)
    tree = load_tree(project_id)
    if tree is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        ideas = ollama_client.generate_root_ideas(
            payload.idea, payload.style, payload.count
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    root = IdeaNode(
        project_id=project_id,
        parent_id=None,
        depth=0,
        title=payload.idea.strip()[:200],
        summary=payload.idea.strip(),
        status="active",  # type: ignore[arg-type]
    )
    children = [
        IdeaNode(
            project_id=project_id,
            parent_id=root.id,
            depth=1,
            title=item["title"] or f"Idea {i + 1}",
            summary=item["summary"],
            hook=item["hook"],
            conflict=item["conflict"],
            cliffhanger=item["cliffhanger"],
        )
        for i, item in enumerate(ideas)
    ]
    # Si ya había raíz, las nuevas ideas cuelgan de la raíz existente.
    if tree["root_id"] and tree["root_id"] in tree["nodes"]:
        for child in children:
            child.parent_id = tree["root_id"]
            child.depth = tree["nodes"][tree["root_id"]].get("depth", 0) + 1
        add_nodes(project_id, children)
        created = children
    else:
        add_nodes(project_id, [root, *children])
        created = [root, *children]
    return {"created": [n.model_dump() for n in created], "tree": load_tree(project_id)}


@router.post("/{node_id}/children")
def api_generate_children(
    project_id: str, node_id: str, payload: ChildrenRequest
) -> dict:
    _require_project(project_id)
    path = branch_path(project_id, node_id)
    if path is None:
        raise HTTPException(status_code=404, detail="node not found")
    try:
        ideas = ollama_client.generate_child_ideas(path, payload.count)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    parent = path[-1]
    children = [
        IdeaNode(
            project_id=project_id,
            parent_id=node_id,
            depth=parent.get("depth", 0) + 1,
            title=item["title"] or f"Subidea {i + 1}",
            summary=item["summary"],
            hook=item["hook"],
            conflict=item["conflict"],
            cliffhanger=item["cliffhanger"],
        )
        for i, item in enumerate(ideas)
    ]
    add_nodes(project_id, children)
    return {"created": [n.model_dump() for n in children], "tree": load_tree(project_id)}


@router.patch("/{node_id}")
def api_set_status(project_id: str, node_id: str, payload: StatusRequest) -> dict:
    _require_project(project_id)
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status inválido. Válidos: {sorted(VALID_STATUSES)}",
        )
    node = set_node_status(project_id, node_id, payload.status)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return node
