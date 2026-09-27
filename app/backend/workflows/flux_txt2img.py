"""Workflow FLUX.1-schnell txt2img 9:16 para ComfyUI API (Phase 11, opcional).

Pesos necesarios (NO descargados por defecto, ~22 GB):
  ComfyUI/models/unet/flux1-schnell-fp8.safetensors      (Comfy-Org/flux1-schnell)
  ComfyUI/models/text_encoders/t5xxl_fp8_e4m3fn.safetensors
  ComfyUI/models/text_encoders/clip_l.safetensors
  ComfyUI/models/vae/ae.safetensors                     (VAE oficial de FLUX)
"""
from __future__ import annotations

import random

UNET = "flux1-schnell-fp8.safetensors"
T5 = "t5xxl_fp8_e4m3fn.safetensors"
CLIP_L = "clip_l.safetensors"
VAE = "ae.safetensors"

PRESETS = {
    "draft": {"width": 768, "height": 1344, "steps": 4},
    "standard": {"width": 832, "height": 1472, "steps": 4},
}


def build_flux_workflow(
    prompt: str,
    preset: str = "draft",
    seed: int | None = None,
    guidance: float = 3.5,
) -> dict:
    if preset not in PRESETS:
        raise ValueError(f"preset inválido: {preset} (válidos: {sorted(PRESETS)})")
    cfg = PRESETS[preset]
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": UNET, "weight_dtype": "default"},
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {"clip_name1": T5, "clip_name2": CLIP_L, "type": "flux"},
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VAE},
        },
        "4": {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": prompt,
                "t5xxl": prompt,
                "guidance": guidance,
            },
        },
        "5": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["4", 0]},
        },
        "6": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {
                "width": cfg["width"],
                "height": cfg["height"],
                "batch_size": 1,
            },
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": cfg["steps"],
                "cfg": 1,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["3", 0]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "storyforge/flux"},
        },
    }
