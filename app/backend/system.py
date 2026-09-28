"""Estado del sistema: qué backends están listos (Phase 19).

Cada chequeo devuelve ok + detalle accionable. Nada lanza excepción.
"""
from __future__ import annotations

import json
import shutil
import urllib.request


def _http_json(url: str, timeout: int = 10) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def check_ollama(host: str = "http://127.0.0.1:11434") -> dict:
    data = _http_json(f"{host}/api/tags")
    if data is None:
        return {"ok": False, "hint": "Ollama no responde. Arráncalo (ollama serve)."}
    models = [m.get("name", "") for m in data.get("models", [])]
    return {"ok": True, "models": models}


def check_comfy(host: str = "http://127.0.0.1:8188") -> dict:
    data = _http_json(f"{host}/system_stats", timeout=15)
    if data is None:
        return {
            "ok": False,
            "hint": "ComfyUI no responde. Arráncalo: py -3.11 main.py (en ComfyUI/).",
        }
    return {"ok": True}


def check_xtts() -> dict:
    try:
        import voice

        ok, missing = voice.model_ready()
        if not ok:
            return {"ok": False, "hint": f"faltan pesos en models/xtts-v2: {missing}"}
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "hint": f"módulo de voz roto: {exc}"}


def check_whisperx() -> dict:
    try:
        import whisperx  # noqa: F401

        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "hint": f"whisperx no instalado: {exc}"}


def check_ffmpeg() -> dict:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return {"ok": True}
    return {"ok": False, "hint": "ffmpeg/ffprobe no están en el PATH."}


def full_status() -> dict:
    return {
        "ollama": check_ollama(),
        "comfyui": check_comfy(),
        "xtts": check_xtts(),
        "whisperx": check_whisperx(),
        "ffmpeg": check_ffmpeg(),
    }
