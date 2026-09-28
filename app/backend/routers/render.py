"""Router de render: export final 9:16 (Phase 17)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import render
from storage import _project_dir, get_project

router = APIRouter(prefix="/api/projects/{project_id}", tags=["render"])


@router.post("/render")
def api_render(project_id: str) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        return {"ok": True, **render.render_project(_project_dir(project_id))}
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/render")
def api_get_render(project_id: str) -> FileResponse:
    final = _project_dir(project_id) / "renders" / "final.mp4"
    if not final.exists():
        raise HTTPException(status_code=404, detail="no hay render: exporta primero")
    return FileResponse(final, media_type="video/mp4", filename=f"{project_id}.mp4")
