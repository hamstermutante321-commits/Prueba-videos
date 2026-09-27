"""Persistencia local de proyectos en projects/<id>/ (docs/07_ARCHITECTURE.md)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models import IdeaNode, Project, ProjectCreate, ProjectSettings, StoryPlan

# .../app/backend -> raíz del proyecto (LocalAIStoryPipeline)
ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT / "projects"


def _project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def create_project(payload: ProjectCreate) -> Project:
    project = Project(
        title=payload.title,
        settings=payload.settings or ProjectSettings(),
    )
    pdir = _project_dir(project.id)
    pdir.mkdir(parents=True, exist_ok=False)
    (pdir / "scenes").mkdir(exist_ok=True)
    (pdir / "renders").mkdir(exist_ok=True)
    _write_json(pdir / "project.json", project.model_dump())
    _write_json(
        pdir / "story_plan.json",
        StoryPlan().model_dump(),
    )
    _write_json(pdir / "idea_tree.json", {"root_id": None, "nodes": {}})
    return project


def get_project(project_id: str) -> Project | None:
    path = _project_dir(project_id) / "project.json"
    if not path.exists():
        return None
    return Project(**_read_json(path))


def list_projects() -> list[Project]:
    if not PROJECTS_DIR.exists():
        return []
    out: list[Project] = []
    for child in sorted(PROJECTS_DIR.iterdir()):
        if not child.is_dir():
            continue
        path = child / "project.json"
        if path.exists():
            out.append(Project(**_read_json(path)))
    return out


def get_story_plan(project_id: str) -> StoryPlan | None:
    path = _project_dir(project_id) / "story_plan.json"
    if not path.exists():
        return None
    return StoryPlan(**_read_json(path))


def touch_updated(project_id: str) -> None:
    path = _project_dir(project_id) / "project.json"
    if not path.exists():
        return
    data = _read_json(path)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(path, data)


# --- Árbol de ideas persistente (docs/09_IDEA_EXPANSION_ENGINE.md) ---

def _tree_path(project_id: str) -> Path:
    return _project_dir(project_id) / "idea_tree.json"


def load_tree(project_id: str) -> dict | None:
    path = _tree_path(project_id)
    if not path.exists():
        return None
    data = _read_json(path)
    data.setdefault("root_id", None)
    data.setdefault("nodes", {})
    data.setdefault("active_node_id", None)
    data.setdefault("selected_story_node_id", None)
    return data


def save_tree(project_id: str, tree: dict) -> None:
    _write_json(_tree_path(project_id), tree)
    touch_updated(project_id)


def add_nodes(project_id: str, nodes: list[IdeaNode]) -> None:
    tree = load_tree(project_id)
    if tree is None:
        raise FileNotFoundError("project not found")
    for node in nodes:
        tree["nodes"][node.id] = node.model_dump()
    if tree["root_id"] is None and nodes:
        tree["root_id"] = nodes[0].id
    save_tree(project_id, tree)


def set_node_status(project_id: str, node_id: str, status: str) -> dict | None:
    tree = load_tree(project_id)
    if tree is None or node_id not in tree["nodes"]:
        return None
    tree["nodes"][node_id]["status"] = status
    if status == "active":
        tree["active_node_id"] = node_id
    if status == "selected_for_story":
        tree["selected_story_node_id"] = node_id
    save_tree(project_id, tree)
    return tree["nodes"][node_id]


def branch_path(project_id: str, node_id: str) -> list[dict] | None:
    """Camino raíz -> ... -> nodo (para dar contexto al LLM)."""
    tree = load_tree(project_id)
    if tree is None or node_id not in tree["nodes"]:
        return None
    path: list[dict] = []
    current: str | None = node_id
    while current:
        node = tree["nodes"].get(current)
        if node is None:
            break
        path.append(node)
        current = node.get("parent_id")
    path.reverse()
    return path
