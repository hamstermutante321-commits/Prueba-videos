"""Router de video: image-to-video con backend seleccionable (cambio_IA.md).

Default: cogvideox_i2v (principal). framepack: secundario (pesos pendientes).
ltx: deprecated pero funcional.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import comfy_client
import video_backends
from adapters import cogvideox, framepack
from storage import _project_dir, get_project, mark_scene_media
from workflows.ltx_img2video import PRESETS as LTX_PRESETS
from workflows.ltx_img2video import build_ltx_workflow

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["video"])


class VideoRequest(BaseModel):
    motion_prompt: str = Field(min_length=3, max_length=2000)
    negative: str = ""
    preset: str = "subtle"
    seed: int | None = None
    backend: str = video_backends.DEFAULT_BACKEND


def _comfy_root() -> Path:
    return _project_dir("__x__").parents[1] / "ComfyUI"


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
    backend = payload.backend
    try:
        info = video_backends.get_backend(backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.preset not in ("still_plus", "subtle", "cinematic", "action"):
        raise HTTPException(status_code=400, detail="preset inválido")
    try:
        if backend == "cogvideox_i2v":
            meta = _run_cogvideox(sdir, payload)
        elif backend == "framepack":
            meta = _run_framepack(sdir, payload)
        else:
            meta = _run_ltx(sdir, payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    (sdir / "video_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    mark_scene_media(
        project_id, scene_id, "video", video_path=f"scenes/{scene_id}/clip.mp4"
    )
    return meta


def _stamp(backend: str, preset: str) -> str:
    return f"clip_{backend}_{preset}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.mp4"


def _run_cogvideox(sdir: Path, payload: VideoRequest) -> dict:
    """Principal: CogVideoX-5B-I2V GGUF Q4 (vertical 480x720 @ 8fps)."""
    uploaded = comfy_client.upload_image(str(sdir / "image.png"))
    workflow = cogvideox.build_cogvideox_workflow(
        uploaded, payload.motion_prompt, payload.negative, payload.preset, payload.seed
    )
    prompt_id = comfy_client.queue_prompt(workflow)
    result = comfy_client.wait_result(prompt_id)
    filename, subfolder = comfy_client.first_video_artifact(result)
    blob = comfy_client.download_view(filename, subfolder)
    out_name = _stamp("cogvideox", payload.preset)
    (sdir / out_name).write_bytes(blob)
    (sdir / "clip.mp4").write_bytes(blob)
    return {
        "file": out_name,
        "backend": "cogvideox_i2v",
        "preset": payload.preset,
        "motion_prompt": payload.motion_prompt,
        "prompt_id": prompt_id,
        "bytes": (sdir / out_name).stat().st_size,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _download_frames(result: dict) -> list[Path]:
    import tempfile

    outs = result.get("outputs", {})
    images: list[dict] = []
    for node_out in outs.values():
        images.extend(node_out.get("images", []))
    pngs = [im for im in images if im.get("filename", "").lower().endswith(".png")]
    if not pngs:
        raise RuntimeError("CogVideoX no produjo frames")
    tmp = Path(tempfile.mkdtemp(prefix="cogframes_"))
    paths = []
    for i, im in enumerate(pngs):
        blob = comfy_client.download_view(im["filename"], im.get("subfolder", ""))
        p = tmp / f"frame{i:04d}.png"
        p.write_bytes(blob)
        paths.append(p)
    return paths


def _run_framepack(sdir: Path, payload: VideoRequest) -> dict:
    """Secundario: FramePack. Falla claro si faltan los pesos (~30 GB)."""
    models_dir = _comfy_root() / "models"
    ok, missing = framepack.check_weights(models_dir)
    if not ok:
        raise RuntimeError(
            "FramePack sin pesos. Descarga a ComfyUI/models: " + ", ".join(missing)
        )
    uploaded = comfy_client.upload_image(str(sdir / "image.png"))
    workflow = framepack.build_framepack_workflow(
        uploaded, payload.motion_prompt, payload.negative, payload.preset, payload.seed
    )
    prompt_id = comfy_client.queue_prompt(workflow)
    result = comfy_client.wait_result(prompt_id)
    frames = _download_frames(result)
    out_name = _stamp("framepack", payload.preset)
    cogvideox.frames_to_mp4(frames, sdir / out_name, fps=24)
    (sdir / "clip.mp4").write_bytes((sdir / out_name).read_bytes())
    return {
        "file": out_name,
        "backend": "framepack",
        "preset": payload.preset,
        "motion_prompt": payload.motion_prompt,
        "prompt_id": prompt_id,
        "bytes": (sdir / out_name).stat().st_size,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _run_ltx(sdir: Path, payload: VideoRequest) -> dict:
    """Deprecated: LTX-Video 2B. Se mantiene funcional, ya no recomendado."""
    if payload.preset not in LTX_PRESETS:
        raise HTTPException(
            status_code=400, detail=f"preset inválido: {sorted(LTX_PRESETS)}"
        )
    uploaded = comfy_client.upload_image(str(sdir / "image.png"))
    workflow = build_ltx_workflow(
        uploaded, payload.motion_prompt, payload.negative, payload.preset, payload.seed
    )
    prompt_id = comfy_client.queue_prompt(workflow)
    result = comfy_client.wait_result(prompt_id)
    filename, subfolder = comfy_client.first_video_artifact(result)
    blob = comfy_client.download_view(filename, subfolder)
    out_name = _stamp("ltx", payload.preset)
    (sdir / out_name).write_bytes(blob)
    (sdir / "clip.mp4").write_bytes(blob)
    return {
        "file": out_name,
        "backend": "ltx",
        "preset": payload.preset,
        "motion_prompt": payload.motion_prompt,
        "prompt_id": prompt_id,
        "comfy_filename": filename,
        "bytes": len(blob),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
