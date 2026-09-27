"""Router de imagen: generar imagen de escena con ComfyUI (Phase 10 SDXL, Phase 11 FLUX)."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import comfy_client
from storage import _project_dir, get_project
from workflows.flux_txt2img import PRESETS as FLUX_PRESETS
from workflows.flux_txt2img import build_flux_workflow
from workflows.sdxl_txt2img import PRESETS as SDXL_PRESETS
from workflows.sdxl_txt2img import build_sdxl_workflow

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["image"])

IMAGE_MODELS = ("sdxl", "flux")


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    negative: str = ""
    preset: str = "draft"
    seed: int | None = None
    model: str = "sdxl"


@router.post("/{scene_id}/image")
def api_generate_image(project_id: str, scene_id: str, payload: ImageRequest) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    sdir = _project_dir(project_id) / "scenes" / scene_id
    if not sdir.exists():
        raise HTTPException(status_code=404, detail="scene not found")
    if payload.model not in IMAGE_MODELS:
        raise HTTPException(
            status_code=400, detail=f"model inválido: {list(IMAGE_MODELS)}"
        )
    presets = SDXL_PRESETS if payload.model == "sdxl" else FLUX_PRESETS
    if payload.preset not in presets:
        raise HTTPException(
            status_code=400, detail=f"preset inválido: {sorted(presets)}"
        )
    try:
        if payload.model == "sdxl":
            workflow = build_sdxl_workflow(
                payload.prompt, payload.negative, payload.preset, payload.seed
            )
        else:
            workflow = build_flux_workflow(
                payload.prompt, payload.preset, payload.seed
            )
        prompt_id = comfy_client.queue_prompt(workflow)
        result = comfy_client.wait_result(prompt_id)
        filename, subfolder = comfy_client.first_image_artifact(result)
        blob = comfy_client.download_view(filename, subfolder)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_name = f"image_{payload.model}_{payload.preset}_{stamp}.png"
    (sdir / out_name).write_bytes(blob)
    # versionado simple: image.png siempre apunta a la ganadora actual
    (sdir / "image.png").write_bytes(blob)
    meta = {
        "file": out_name,
        "model": payload.model,
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
