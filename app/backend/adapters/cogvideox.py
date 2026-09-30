"""Adapter principal: CogVideoX-5B-I2V vía kijai ComfyUI-CogVideoXWrapper (cambio_IA.md).

Ruta GGUF Q4: único modo que cabe en RTX 4060 Ti 8GB (bf16 OOM al cargar).
720 -> se genera en vertical 480x720 @ 8 fps, ideal para 9:16.
Prompts EN INGLÉS, motion-only: el image prompt describió la escena;
aquí solo sujeto + entorno + cámara + continuidad.
Nodos: DownloadAndLoadCogVideoGGUFModel(autodescarga) + CLIPLoader(T5 fp8) +
CogVideoTextEncode x2 + LoadImage + ImageScale + CogVideoImageEncode +
CogVideoSampler + CogVideoDecode + CreateVideo + SaveVideo.

Pesos (auto-descarga el loader a ComfyUI/models/CogVideo/):
  CogVideoX_5b_I2V_GGUF_Q4_0.safetensors (~3 GB)
  + text_encoders/t5xxl_fp8_e4m3fn.safetensors (ya descargado en models/clip/)
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

GGUF_MODEL = "CogVideoX_5b_I2V_GGUF_Q4_0.safetensors"
T5 = "t5xxl_fp8_e4m3fn.safetensors"

NEGATIVE_DEFAULT = (
    "low quality, worst quality, deformed, distorted, disfigured, "
    "motion smear, motion artifacts, fused fingers, bad anatomy, watermark, text"
)

# CogVideoX genera a 8 fps. draft 33f (~4 s), standard 49f (~6 s), todo 480x720.
PRESETS = {
    "still_plus": {"width": 480, "height": 720, "num_frames": 25, "steps": 15, "offload": True},
    "subtle": {"width": 480, "height": 720, "num_frames": 33, "steps": 20, "offload": False},
    "cinematic": {"width": 480, "height": 720, "num_frames": 49, "steps": 25, "offload": False},
    "action": {"width": 480, "height": 720, "num_frames": 49, "steps": 30, "offload": False},
}


def build_cogvideox_workflow(
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
        "1": {
            "class_type": "DownloadAndLoadCogVideoGGUFModel",
            "inputs": {
                "model": GGUF_MODEL,
                "vae_precision": "bf16",
                "fp8_fastmode": False,
                "load_device": "main_device",
                "enable_sequential_cpu_offload": cfg["offload"],
                "attention_mode": "sdpa",
            },
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": T5, "type": "sd3", "device": "default"},
        },
        "3": {
            "class_type": "CogVideoTextEncode",
            "inputs": {"clip": ["2", 0], "prompt": prompt, "strength": 1.0, "force_offload": True},
        },
        "4": {
            "class_type": "CogVideoTextEncode",
            "inputs": {"clip": ["2", 0], "prompt": neg, "strength": 1.0, "force_offload": True},
        },
        "5": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename, "upload": "image"},
        },
        "6": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["5", 0],
                "upscale_method": "lanczos",
                "width": cfg["width"],
                "height": cfg["height"],
                "crop": "center",
            },
        },
        "7": {
            "class_type": "CogVideoImageEncode",
            "inputs": {
                "vae": ["1", 1],
                "start_image": ["6", 0],
                "enable_tiling": True,
                "noise_aug_strength": 0.0,
                "strength": 1.0,
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        },
        "8": {
            "class_type": "CogVideoSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "num_frames": cfg["num_frames"],
                "steps": cfg["steps"],
                "cfg": 6.0,
                "seed": seed,
                "scheduler": "CogVideoXDPMScheduler",
                "image_cond_latents": ["7", 0],
                "denoise_strength": 1.0,
            },
        },
        "9": {
            "class_type": "CogVideoDecode",
            "inputs": {
                "vae": ["1", 1],
                "samples": ["8", 0],
                "enable_vae_tiling": True,
                "tile_sample_min_height": 240,
                "tile_sample_min_width": 360,
                "tile_overlap_factor_height": 0.2,
                "tile_overlap_factor_width": 0.2,
                "auto_tile_size": True,
            },
        },
        "10": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["9", 0], "fps": 8},
        },
        "11": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["10", 0],
                "filename_prefix": "storyforge/cogvideox",
                "format": "auto",
                "codec": "auto",
            },
        },
    }


def frames_to_mp4(frames: list[Path], out_mp4: Path, fps: int = 8) -> Path:
    """Ensambla frames PNG en mp4 (ruta FramePack)."""
    import tempfile

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for i, fr in enumerate(frames):
            (Path(tmp) / f"f{i:04d}.png").write_bytes(fr.read_bytes())
        cmd = [
            "ffmpeg", "-y", "-framerate", str(fps), "-i",
            str(Path(tmp) / "f%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-movflags", "+faststart", str(out_mp4),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0 or not out_mp4.exists():
            raise RuntimeError(f"ffmpeg no pudo ensamblar frames: {proc.stderr[-500:]}")
    return out_mp4
