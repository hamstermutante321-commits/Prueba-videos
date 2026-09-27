"""Router de imagen: generar imagen de escena con ComfyUI + SDXL (Phase 10)."""
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import comfy_client
from storage import _project_dir, get_project
from workflows.sdxl_txt2img import PRESETS, build_sdxl_workflow

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["image"])


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    negative: str = ""
    preset: str = "draft"
    seed: int | None = None


@router.post("/{scene_id}/image")
def api_generate_image(project_id: str, scene_id: str, payload: ImageRequest) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    sdir = _project_dir(project_id) / "scenes" / scene_id
    if not sdir.exists():
        raise HTTPException(status_code=404, detail="scene not found")
    if payload.preset not in PRESETS:
        raise HTTPException(
            status_code=400, detail=f"preset inválido: {sorted(PRESETS)}"
        )
    try:
        workflow = build_sdxl_workflow(
            payload.prompt, payload.negative, payload.preset, payload.seed
        )
        prompt_id = comfy_client.queue_prompt(workflow)
        result = comfy_client.wait_result(prompt_id)
        filename, subfolder = comfy_client.first_image_artifact(result)
        blob = comfy_client.download_view(filename, subfolder)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_name = f"image_{payload.preset}_{stamp}.png"
    (sdir / out_name).write_bytes(blob)
    # versionado simple: image.png siempre apunta a la ganadora actual
    (sdir / "image.png").write_bytes(blob)
    meta = {
        "file": out_name,
        "preset": payload.preset,
        "prompt": payload.prompt,
        "negative": payload.negative,
        "prompt_id": prompt_id,
        "comfy_filename": filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(sdir / "image_meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    return meta
