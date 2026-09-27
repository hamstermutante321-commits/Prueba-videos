"""Router de video: animar imagen de escena con ComfyUI + LTX-Video (Phase 12)."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import comfy_client
from storage import _project_dir, get_project
from workflows.ltx_img2video import PRESETS, build_ltx_workflow

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["video"])


class VideoRequest(BaseModel):
    motion_prompt: str = Field(min_length=3, max_length=4000)
    negative: str = ""
    preset: str = "subtle"
    seed: int | None = None


@router.post("/{scene_id}/video")
def api_generate_video(project_id: str, scene_id: str, payload: VideoRequest) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    sdir = _project_dir(project_id) / "scenes" / scene_id
    if not sdir.exists():
        raise HTTPException(status_code=404, detail="scene not found")
    image_path = sdir / "image.png"
    if not image_path.exists():
        raise HTTPException(
            status_code=400,
            detail="la escena no tiene image.png: genera la imagen primero",
        )
    if payload.preset not in PRESETS:
        raise HTTPException(
            status_code=400, detail=f"preset inválido: {sorted(PRESETS)}"
        )
    try:
        uploaded = comfy_client.upload_image(str(image_path))
        workflow = build_ltx_workflow(
            uploaded,
            payload.motion_prompt,
            payload.negative,
            payload.preset,
            payload.seed,
        )
        prompt_id = comfy_client.queue_prompt(workflow)
        result = comfy_client.wait_result(prompt_id)
        filename, subfolder = comfy_client.first_video_artifact(result)
        blob = comfy_client.download_view(filename, subfolder)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_name = f"clip_{payload.preset}_{stamp}.mp4"
    (sdir / out_name).write_bytes(blob)
    (sdir / "clip.mp4").write_bytes(blob)
    meta = {
        "file": out_name,
        "backend": "ltx-video-2b",
        "preset": payload.preset,
        "motion_prompt": payload.motion_prompt,
        "prompt_id": prompt_id,
        "comfy_filename": filename,
        "bytes": len(blob),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(sdir / "video_meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    return meta
