"""Persistencia local de proyectos en projects/<id>/ (docs/07_ARCHITECTURE.md)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models import Project, ProjectCreate, ProjectSettings, StoryPlan

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
