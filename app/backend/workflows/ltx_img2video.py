"""Workflow LTX-Video 2B image-to-video 9:16 (Phase 12).

Basado en la plantilla oficial "LTXV Image to Video" (Comfy-Org/workflow_templates).
Pesos: checkpoints/ltx-video-2b-v0.9.5.safetensors + text_encoders/t5xxl_fp16.safetensors.
"""
from __future__ import annotations

import random

CHECKPOINT = "ltx-video-2b-v0.9.5.safetensors"
T5 = "t5xxl_fp16.safetensors"

NEGATIVE_DEFAULT = (
    "low quality, worst quality, deformed, distorted, disfigured, "
    "motion smear, motion artifacts, fused fingers, bad anatomy, weird hand, ugly"
)

# preset: tamaño, frames (24 fps), fuerza de condicionado, pasos
PRESETS = {
    "still_plus": {"width": 512, "height": 768, "length": 25, "strength": 0.05, "steps": 25},
    "subtle": {"width": 512, "height": 768, "length": 49, "strength": 0.15, "steps": 25},
    "cinematic": {"width": 704, "height": 1024, "length": 97, "strength": 0.30, "steps": 30},
    "action": {"width": 704, "height": 1024, "length": 97, "strength": 0.50, "steps": 30},
}


def build_ltx_workflow(
    image_filename: str,
    prompt: str,
    negative: str = "",
    preset: str = "subtle",
    seed: int | None = None,
) -> dict:
    if preset not in PRESETS:
        raise ValueError(f"preset inválido: {preset} (válidos: {sorted(PRESETS)})")
    cfg = PRESETS[preset]
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    neg = negative.strip() or NEGATIVE_DEFAULT
    return {
        "44": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CHECKPOINT},
        },
        "38": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": T5, "type": "ltxv", "device": "default"},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["38", 0]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": neg, "clip": ["38", 0]},
        },
        "78": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename, "upload": "image"},
        },
        "77": {
            "class_type": "LTXVImgToVideo",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "vae": ["44", 2],
                "image": ["78", 0],
                "width": cfg["width"],
                "height": cfg["height"],
                "length": cfg["length"],
                "batch_size": 1,
                "strength": cfg["strength"],
            },
        },
        "69": {
            "class_type": "LTXVConditioning",
            "inputs": {
                "positive": ["77", 0],
                "negative": ["77", 1],
                "frame_rate": 25.0,
            },
        },
        "73": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "euler"},
        },
        "71": {
            "class_type": "LTXVScheduler",
            "inputs": {
                "steps": cfg["steps"],
                "max_shift": 2.05,
                "base_shift": 0.95,
                "stretch": True,
                "terminal": 0.1,
                "latent": ["77", 2],
            },
        },
        "72": {
            "class_type": "SamplerCustom",
            "inputs": {
                "model": ["44", 0],
                "positive": ["69", 0],
                "negative": ["69", 1],
                "sampler": ["73", 0],
                "sigmas": ["71", 0],
                "latent_image": ["77", 2],
                "add_noise": True,
                "noise_seed": seed,
                "cfg": 3,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["72", 0], "vae": ["44", 2]},
        },
        "80": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["8", 0], "fps": 24},
        },
        "81": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["80", 0],
                "filename_prefix": "storyforge/ltxv",
                "format": "auto",
                "codec": "auto",
            },
        },
    }
