"""Cliente de ComfyUI por API local (Phase 9).

Encola workflows (/prompt), espera resultado (/history) y descarga
la imagen (/view). Solo stdlib.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

COMFY_HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")


def _req(method: str, path: str, data: dict | None = None, timeout: int = 60):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        COMFY_HOST + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"ComfyUI no responde en {COMFY_HOST}. "
            f"Arráncalo con: py -3.11 main.py (en ComfyUI/). Detalle: {exc}"
        ) from exc
    ctype = ""
    try:
        ctype = r.headers.get_content_type()
    except Exception:
        pass
    if "json" in ctype:
        return json.loads(raw.decode())
    return raw


def system_stats() -> dict:
    return _req("GET", "/system_stats")


def queue_prompt(workflow: dict) -> str:
    res = _req("POST", "/prompt", {"prompt": workflow}, timeout=120)
    prompt_id = res.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI no devolvió prompt_id: {str(res)[:300]}")
    return prompt_id


def wait_result(prompt_id: str, timeout_s: int = 1200, poll_s: int = 2) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        history = _req("GET", f"/history/{prompt_id}", timeout=60)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_s)
    raise RuntimeError(f"ComfyUI tardó más de {timeout_s}s en el prompt {prompt_id}")


def download_view(filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
    from urllib.parse import urlencode

    query = urlencode(
        {"filename": filename, "subfolder": subfolder, "type": folder_type}
    )
    req = urllib.request.Request(f"{COMFY_HOST}/view?{query}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No pude descargar {filename} de ComfyUI: {exc}") from exc


def first_image_artifact(result: dict) -> tuple[str, str]:
    """Devuelve (filename, subfolder) de la primera imagen del resultado."""
    for node_id, node_out in result.get("outputs", {}).items():
        for img in node_out.get("images", []):
            return img["filename"], img.get("subfolder", "")
    raise RuntimeError("El workflow no produjo ninguna imagen")
