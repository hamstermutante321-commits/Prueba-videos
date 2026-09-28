"""Router de subtítulos: WhisperX + bloques + ASS (Phase 15/16)."""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import subs
from captions import STYLES, blocks_to_ass, build_blocks
from storage import _project_dir, get_project, mark_scene_media

router = APIRouter(prefix="/api/projects/{project_id}/scenes", tags=["subtitles"])


class SubtitleRequest(BaseModel):
    language: str = "es"


class AssRequest(BaseModel):
    style: str = "classic"
    max_chars_per_line: int = Field(default=24, ge=10, le=42)
    font_scale: float = Field(default=1.0, ge=0.6, le=1.6)
    margin_v: int = Field(default=320, ge=0, le=900)


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


@router.post("/{scene_id}/subtitles/ass")
def api_make_ass(project_id: str, scene_id: str, payload: AssRequest) -> dict:
    if payload.style not in STYLES:
        raise HTTPException(
            status_code=400, detail=f"estilo inválido: {sorted(STYLES)}"
        )
    sdir = _project_dir(project_id) / "scenes" / scene_id
    words_file = sdir / "subtitles.json"
    if not words_file.exists():
        raise HTTPException(
            status_code=400,
            detail="no hay subtitles.json: transcribe primero",
        )
    data = json.loads(words_file.read_text(encoding="utf-8"))
    blocks = build_blocks(
        data.get("words", []), max_chars_per_line=payload.max_chars_per_line
    )
    ass = blocks_to_ass(
        blocks,
        data.get("words", []),
        style=payload.style,
        margin_v=payload.margin_v,
        font_scale=payload.font_scale,
    )
    (sdir / "subtitles_blocks.json").write_text(
        json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (sdir / "subtitles.ass").write_text(ass, encoding="utf-8")
    mark_scene_media(
        project_id,
        scene_id,
        "subtitle",
        subtitle_ass_path=f"scenes/{scene_id}/subtitles.ass",
    )
    return {"ok": True, "style": payload.style, "blocks": blocks}
