"""Registro de backends image-to-video.

- wan_i2v: PRINCIPAL y default (Wan 2.2 I2V-A14B + LightX2V 4-step, Q4_K_M).
- cogvideox_i2v: secundario (reemplazado; GGUF Q4 vertical 480x720).
- framepack: secundario (videos largos/continuidad, prompts cortos; pesos pendientes).
- ltx: deprecated SIN pesos (se borraron para hacer sitio; el código queda).
"""
from __future__ import annotations

DEFAULT_BACKEND = "wan_i2v"

BACKENDS = {
    "wan_i2v": {
        "label": "Wan 2.2 I2V-A14B + LightX2V 4-step (recomendado)",
        "role": "primary",
        "notes": "Default. Q4_K_M + TeaCache + block-swap: corre en 8 GB VRAM. 480x832@16fps.",
    },
    "cogvideox_i2v": {
        "label": "CogVideoX-5B-I2V (secundario)",
        "role": "secondary",
        "notes": "Reemplazado por Wan. GGUF Q4, 480x720@8fps vertical.",
    },
    "framepack": {
        "label": "FramePack (alternativa)",
        "role": "secondary",
        "notes": "Videos más largos/continuidad. Prompts cortos de movimiento. Requiere ~30 GB en pesos (no instalado).",
    },
    "ltx": {
        "label": "LTX-Video 2B (deprecated, sin pesos)",
        "role": "deprecated",
        "notes": "Pesos borrados. Solo queda el código por compatibilidad.",
    },
}


def get_backend(name: str) -> dict:
    if name not in BACKENDS:
        raise ValueError(f"backend inválido: {name} (válidos: {sorted(BACKENDS)})")
    info = {"name": name, **BACKENDS[name]}
    return info


def list_backends() -> list[dict]:
    order = ["wan_i2v", "cogvideox_i2v", "framepack", "ltx"]
    return [get_backend(n) for n in order if n in BACKENDS]
