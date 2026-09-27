"""Workflow SDXL txt2img 9:16 para ComfyUI API (Phase 10).

Grafo mínimo: CheckpointLoader -> CLIPTextEncode(+/-) -> KSampler ->
VAEDecode -> SaveImage. Tamaños por preset (docs/10_IMAGE_GENERATION_SPEC.md).
"""
from __future__ import annotations

import random

CHECKPOINT = "sd_xl_base_1.0.safetensors"

PRESETS = {
    # lado corto moderado para iterar rápido en 8GB VRAM
    "draft": {"width": 768, "height": 1344, "steps": 20, "cfg": 6.0},
    "standard": {"width": 832, "height": 1472, "steps": 28, "cfg": 6.5},
}

NEGATIVE_DEFAULT = (
    "blurry, low quality, distorted, deformed, watermark, text, "
    "extra limbs, bad anatomy"
)


def build_sdxl_workflow(
    prompt: str,
    negative: str = "",
    preset: str = "draft",
    seed: int | None = None,
) -> dict:
    if preset not in PRESETS:
        raise ValueError(f"preset inválido: {preset} (válidos: {sorted(PRESETS)})")
    cfg = PRESETS[preset]
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    neg = negative.strip() or NEGATIVE_DEFAULT
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CHECKPOINT},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": neg, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": cfg["width"],
                "height": cfg["height"],
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": cfg["steps"],
                "cfg": cfg["cfg"],
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": "storyforge/sdxl"},
        },
    }
