"""Estado del sistema: qué backends están listos (Phase 19).

Cada chequeo devuelve ok + detalle accionable. Nada lanza excepción.
"""
from __future__ import annotations

import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMFY_MODELS = ROOT / "ComfyUI" / "models"


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


def check_cogvideox() -> dict:
    dit = COMFY_MODELS / "diffusion_models" / "CogVideoX_1_0_5b_I2V_bf16.safetensors"
    vae = COMFY_MODELS / "vae" / "cogvideox_vae_bf16.safetensors"
    t5 = COMFY_MODELS / "clip" / "text_encoders" / "t5xxl_fp8_e4m3fn.safetensors"
    t5_alt = COMFY_MODELS / "text_encoders" / "t5xxl_fp8_e4m3fn.safetensors"
    t5_ok = t5.exists() or t5_alt.exists()
    missing = [str(p) for p, ok in ((dit, dit.exists()), (vae, vae.exists()), (t5, t5_ok)) if not ok]
    if missing:
        return {"ok": False, "hint": f"faltan pesos CogVideoX: {missing}"}
    return {"ok": True}


def check_framepack() -> dict:
    return {
        "ok": False,
        "hint": "FramePack no instalado (requiere ~30 GB en pesos HunyuanVideo). Secundario.",
    }


def full_status() -> dict:
    return {
        "ollama": check_ollama(),
        "comfyui": check_comfy(),
        "cogvideox_i2v": check_cogvideox(),
        "framepack": check_framepack(),
        "xtts": check_xtts(),
        "whisperx": check_whisperx(),
        "ffmpeg": check_ffmpeg(),
    }
