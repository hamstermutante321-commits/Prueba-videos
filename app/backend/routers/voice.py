"""Router de voz: subir referencia y generar narración por escena (Phase 14)."""
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import voice
from storage import _project_dir, get_project, mark_scene_media

router = APIRouter(prefix="/api/projects/{project_id}", tags=["voice"])

ALLOWED_EXT = {".mp4", ".mp3", ".wav", ".m4a"}


class ReferenceRequest(BaseModel):
    start: float = 0.0
    seconds: float = Field(default=20.0, ge=3.0, le=60.0)


class NarrationRequest(BaseModel):
    text: str = ""  # vacío = usar narration.txt de la escena
    language: str = "es"


def _voice_dir(project_id: str) -> Path:
    d = _project_dir(project_id) / "voice"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.get("/voice/status")
def api_voice_status(project_id: str) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    ok, missing = voice.model_ready()
    ref = _voice_dir(project_id) / "reference.wav"
    return {
        "model_ready": ok,
        "missing_files": missing,
        "has_reference": ref.exists(),
    }


@router.post("/voice/reference")
async def api_upload_reference(
    project_id: str, file: UploadFile, start: float = 0.0, seconds: float = 20.0
) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400, detail=f"formato no soportado: {sorted(ALLOWED_EXT)}"
        )
    vdir = _voice_dir(project_id)
    orig = vdir / f"reference_orig{ext}"
    with open(orig, "wb") as fh:
        shutil.copyfileobj(file.file, fh)
    try:
        info = voice.extract_reference(orig, vdir / "reference.wav", start, seconds)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True, **info}


@router.get("/voice/reference")
def api_get_reference(project_id: str) -> FileResponse:
    ref = _voice_dir(project_id) / "reference.wav"
    if not ref.exists():
        raise HTTPException(status_code=404, detail="no hay referencia")
    return FileResponse(ref, media_type="audio/wav", filename="reference.wav")


@router.post("/scenes/{scene_id}/narration")
def api_narrate(project_id: str, scene_id: str, payload: NarrationRequest) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    sdir = _project_dir(project_id) / "scenes" / scene_id
    if not sdir.exists():
        raise HTTPException(status_code=404, detail="scene not found")
    text = payload.text.strip()
    if not text:
        narr_file = sdir / "narration.txt"
        if narr_file.exists():
            text = narr_file.read_text(encoding="utf-8").strip()
    if not text:
        raise HTTPException(status_code=400, detail="texto vacío y sin narration.txt")
    ref = _voice_dir(project_id) / "reference.wav"
    try:
        info = voice.synthesize(text, ref, sdir / "voice.wav", payload.language)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    (sdir / "narration.txt").write_text(text, encoding="utf-8")
    mark_scene_media(
        project_id, scene_id, "audio", audio_path=f"scenes/{scene_id}/voice.wav"
    )
    return {"ok": True, "text": text, **info}


@router.get("/scenes/{scene_id}/narration")
def api_get_narration(project_id: str, scene_id: str) -> FileResponse:
    wav = _project_dir(project_id) / "scenes" / scene_id / "voice.wav"
    if not wav.exists():
        raise HTTPException(status_code=404, detail="no hay narración")
    return FileResponse(wav, media_type="audio/wav", filename=f"{scene_id}.wav")
