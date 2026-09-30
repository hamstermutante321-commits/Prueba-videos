"""Adapter secundario: FramePack (HunyuanVideo I2V) vía Kijai FramePackWrapper.

Útil para videos más largos o continuidad. Prompts CORTOS y solo movimiento.
PESOS PENDIENTES (~30 GB, no caben junto al resto ahora mismo):
  diffusion_models/FramePackI2V_HY_fp8_e4m3fn.safetensors (lllyasviel/FramePackI2V_HY)
  text_encoders/clip_l.safetensors + llava_llama3 (fp8)
  vae/hunyuan_video_vae_bf16.safetensors + sigclip vision
Sin esos archivos el adapter falla con mensaje claro (no a mitad del workflow).
"""
from __future__ import annotations

from pathlib import Path

REQUIRED = {
    "transformer": "diffusion_models/FramePackI2V_HY_fp8_e4m3fn.safetensors",
    "clip_l": "text_encoders/clip_l.safetensors",
    "vae": "vae/hunyuan_video_vae_bf16.safetensors",
}

PRESETS = {
    "still_plus": {"length": 25},
    "subtle": {"length": 49},
    "cinematic": {"length": 97},
    "action": {"length": 121},
}


def check_weights(models_dir: Path) -> tuple[bool, list[str]]:
    missing = [rel for rel in REQUIRED.values() if not (models_dir / rel).exists()]
    return (len(missing) == 0, missing)


def build_framepack_workflow(
    image_filename: str,
    prompt: str,
    negative: str = "",
    preset: str = "subtle",
    seed: int | None = None,
) -> dict:
    """Workflow HunyuanVideo-I2V simplificado (NO probado en vivo aún)."""
    import random

    if preset not in PRESETS:
        raise ValueError(f"preset inválido: {preset} (válidos: {sorted(PRESETS)})")
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    length = PRESETS[preset]["length"]
    return {
        "52": {
            "class_type": "LoadFramePackModel",
            "inputs": {
                "model": REQUIRED["transformer"].split("/")[-1],
                "base_precision": "bf16",
                "quantization": "fp8_e4m3fn",
                "load_device": "offload_device",
                "attention_mode": "sdpa",
            },
        },
        "13": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": REQUIRED["clip_l"].split("/")[-1],
                "clip_name2": "llava_llama3_fp8.safetensors",
                "type": "hunyuan_video",
                "device": "default",
            },
        },
        "12": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": REQUIRED["vae"].split("/")[-1]},
        },
        "47": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["13", 0]},
        },
        "15": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["47", 0]},
        },
        "58": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename, "upload": "image"},
        },
        "39": {
            "class_type": "FramePackSampler",
            "inputs": {
                "model": ["52", 0],
                "positive": ["47", 0],
                "negative": ["15", 0],
                "image": ["58", 0],
                "length": length,
                "seed": seed,
                "steps": 30,
                "cfg": 6.0,
                "scheduler": "unipc_bh1",
            },
        },
        "33": {
            "class_type": "VAEDecodeTiled",
            "inputs": {
                "samples": ["39", 0],
                "vae": ["12", 0],
                "tile_size": 256,
            },
        },
        "70": {
            "class_type": "SaveImage",
            "inputs": {"images": ["33", 0], "filename_prefix": "storyforge/framepack"},
        },
    }
