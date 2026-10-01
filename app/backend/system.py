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


def check_wan() -> dict:
    files = [
        COMFY_MODELS / "diffusion_models" / "high_noise_260412"
        / "wan2.2_i2v_A14b_high_noise_lightx2v_4step_720p_260412-Q4_K_M.gguf",
        COMFY_MODELS / "diffusion_models" / "low_noise_260412"
        / "wan2.2_i2v_A14b_low_noise_lightx2v_4step_720p_260412-Q4_K_M.gguf",
        COMFY_MODELS / "text_encoders" / "umt5-xxl-enc-fp8_e4m3fn.safetensors",
        COMFY_MODELS / "vae" / "Wan2_1_VAE_bf16.safetensors",
    ]
    missing = [p.name for p in files if not p.exists()]
    if missing:
        return {"ok": False, "hint": f"faltan pesos Wan 2.2: {missing}"}
    return {"ok": True, "notes": "Q4_K_M + LightX2V 4-step. SageAttention no disponible en este Windows (sdpa)."}


def check_cogvideox() -> dict:
    gguf = list((COMFY_MODELS / "CogVideo").rglob("*I2V*Q4*.safetensors")) if (COMFY_MODELS / "CogVideo").exists() else []
    if not gguf:
        return {"ok": False, "hint": "CogVideoX secundario: GGUF no descargado (se auto-descarga al usar)."}
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
        "wan_i2v": check_wan(),
        "cogvideox_i2v": check_cogvideox(),
        "framepack": check_framepack(),
        "xtts": check_xtts(),
        "whisperx": check_whisperx(),
        "ffmpeg": check_ffmpeg(),
    }
