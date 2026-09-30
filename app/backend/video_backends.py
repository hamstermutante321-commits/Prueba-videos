"""Registro de backends image-to-video (cambio_IA.md).

- cogvideox_i2v: PRINCIPAL y default (mejor fidelidad + prompt-following).
- framepack: secundario (videos largos/continuidad, prompts cortos de movimiento).
- ltx: deprecated (distorsiona y sigue mal los prompts; se mantiene por compat).
"""
from __future__ import annotations

DEFAULT_BACKEND = "cogvideox_i2v"

BACKENDS = {
    "cogvideox_i2v": {
        "label": "CogVideoX-5B-I2V (recomendado)",
        "role": "primary",
        "notes": "Default. bf16 + fp8 + offload en 8 GB VRAM. 720x480@8fps (el renderer recorta a 9:16).",
    },
    "framepack": {
        "label": "FramePack (alternativa)",
        "role": "secondary",
        "notes": "Videos más largos/continuidad. Prompts cortos de movimiento. Requiere ~30 GB en pesos (no instalado).",
    },
    "ltx": {
        "label": "LTX-Video 2B (deprecated)",
        "role": "deprecated",
        "notes": "Se mantiene por compatibilidad. Distorsiona y sigue mal el motion prompt.",
    },
}


def get_backend(name: str) -> dict:
    if name not in BACKENDS:
        raise ValueError(f"backend inválido: {name} (válidos: {sorted(BACKENDS)})")
    info = {"name": name, **BACKENDS[name]}
    return info


def list_backends() -> list[dict]:
    order = ["cogvideox_i2v", "framepack", "ltx"]
    return [get_backend(n) for n in order if n in BACKENDS]
