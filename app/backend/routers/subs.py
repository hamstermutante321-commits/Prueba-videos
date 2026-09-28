"""Router de subtítulos: transcribir narración con WhisperX (Phase 15)."""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import subs
from storage import _project_dir, get_project

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["subtitles"])


class SubtitleRequest(BaseModel):
    language: str = "es"


@router.post("/{scene_id}/subtitles")
def api_make_subtitles(
    project_id: str, scene_id: str, payload: SubtitleRequest
) -> dict:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    sdir = _project_dir(project_id) / "scenes" / scene_id
    wav = sdir / "voice.wav"
    if not wav.exists():
        raise HTTPException(
            status_code=400,
            detail="la escena no tiene voice.wav: genera la narración primero",
        )
    try:
        data = subs.transcribe_words(wav, payload.language)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    out = sdir / "subtitles.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "language": data["language"],
        "words": len(data["words"]),
        "segments": len(data["segments"]),
        "text": " ".join(w["word"] for w in data["words"])[:300],
    }
