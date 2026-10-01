"""Router de video: image-to-video con backend seleccionable.

Default: wan_i2v (Wan 2.2 I2V-A14B + LightX2V 4-step). cogvideox_i2v: secundario.
framepack: secundario (pesos pendientes). ltx: deprecated sin pesos.
"""
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import comfy_client
import video_backends
from adapters import cogvideox, framepack, wan
from storage import _project_dir, get_project, mark_scene_media
from workflows.ltx_img2video import PRESETS as LTX_PRESETS
from workflows.ltx_img2video import build_ltx_workflow

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["video"])


class VideoRequest(BaseModel):
    motion_prompt: str = Field(min_length=3, max_length=2000)
    negative: str = ""
    preset: str = "subtle"  # solo backends legacy (cogvideox/ltx)
    seed: int | None = None
    backend: str = video_backends.DEFAULT_BACKEND
    # --- Wan 2.2 ---
    mode: str = "fast"  # fast | final
    seconds: float = Field(default=3.0, ge=1.0, le=6.0)
    teacache: float = Field(default=-1.0, ge=-1.0, le=1.0)  # -1 = default del modo
    interpolate: bool = True
    upscaler: str = "anime"  # anime | general | none
    out_fps: int = Field(default=32, ge=8, le=60)


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
    if backend in ("cogvideox_i2v", "ltx") and payload.preset not in (
        "still_plus", "subtle", "cinematic", "action",
    ):
        raise HTTPException(status_code=400, detail="preset inválido")
    if backend == "wan_i2v" and payload.mode not in ("fast", "final"):
        raise HTTPException(status_code=400, detail="mode inválido: fast|final")
    if backend == "wan_i2v" and payload.upscaler not in ("anime", "general", "none"):
        raise HTTPException(status_code=400, detail="upscaler inválido")
    try:
        if backend == "wan_i2v":
            meta = _run_wan(sdir, payload)
        elif backend == "cogvideox_i2v":
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


def _run_wan(sdir: Path, payload: VideoRequest) -> dict:
    """Principal: Wan 2.2 I2V-A14B + LightX2V 4-step.

    FAST: base 480x832 (sin RIFE/upscale). FINAL: RIFE x2 + Real-ESRGAN x4
    y export 1080x1920 H.264. Tiempos medidos por etapa en meta["timings"].
    """
    import time

    t_all, timings = time.time(), {}
    tc = None if payload.teacache < 0 else payload.teacache
    uploaded = comfy_client.upload_image(str(sdir / "image.png"))
    timings["upload_s"] = round(time.time() - t_all, 1)

    wf = wan.build_wan_workflow(
        uploaded,
        payload.motion_prompt,
        payload.negative,
        mode=payload.mode,
        seconds=payload.seconds,
        seed=payload.seed,
        teacache=tc,
        rife=(payload.interpolate if payload.mode == "final" else False),
        upscaler=(payload.upscaler if payload.mode == "final" else "none"),
    )
    t0 = time.time()
    prompt_id = comfy_client.queue_prompt(wf)
    result = comfy_client.wait_result(prompt_id, timeout_s=2400)
    timings["comfyui_s"] = round(time.time() - t0, 1)

    t0 = time.time()
    outs = result.get("outputs", {})
    # Nodo 53 = SaveImage final (con post); 31 = base (sin post). Nunca mezclar.
    has_post = (payload.mode == "final" and (payload.interpolate or payload.upscaler != "none"))
    final_node = "53" if has_post else "31"
    node_out = outs.get(final_node, {})
    pngs = [
        im for im in node_out.get("images", [])
        if im.get("filename", "").lower().endswith(".png")
    ]
    if not pngs:
        # fallback: cualquier PNG (validación laxa, p.ej. backends legacy)
        pngs = [
            im for o in outs.values() for im in o.get("images", [])
            if im.get("filename", "").lower().endswith(".png")
        ]
    if not pngs:
        raise RuntimeError("Wan no produjo frames")
    tmp = Path(tempfile.mkdtemp(prefix="wanframes_"))
    for i, im in enumerate(pngs):
        (tmp / f"f{i:04d}.png").write_bytes(
            comfy_client.download_view(im["filename"], im.get("subfolder", ""))
        )
    timings["download_s"] = round(time.time() - t0, 1)

    # ¿A qué resolución salieron? (FINAL = upscalados x4)
    from PIL import Image

    w0, h0 = Image.open(tmp / "f0000.png").size
    n = len(pngs)
    fps = payload.out_fps if payload.mode == "final" and payload.interpolate else wan.FPS
    out_name = f"clip_wan_{payload.mode}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.mp4"
    out_path = sdir / out_name

    t0 = time.time()
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p"
    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps), "-i", str(tmp / "f%04d.png"),
        "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart", str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"ffmpeg export falló: {proc.stderr[-500:]}")
    timings["export_s"] = round(time.time() - t0, 1)
    timings["total_s"] = round(time.time() - t_all, 1)
    (sdir / "clip.mp4").write_bytes(out_path.read_bytes())
    vram = _vram_used_mb()
    return {
        "file": out_name,
        "backend": "wan_i2v",
        "mode": payload.mode,
        "frames": n,
        "base_resolution": f"{w0}x{h0}",
        "final_resolution": "1080x1920",
        "fps": fps,
        "motion_prompt": payload.motion_prompt,
        "prompt_id": prompt_id,
        "bytes": out_path.stat().st_size,
        "vram_used_mb": vram,
        "timings": timings,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _vram_used_mb() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30,
        )
        return int(out.stdout.strip().split()[0])
    except Exception:
        return None


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
