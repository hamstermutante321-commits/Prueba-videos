"""Adapter principal: Wan 2.2 I2V-A14B + LightX2V 4-step (Q4_K_M GGUF).

Dual-stage HIGH -> LOW con handoff de latentes. 480x832 @ 16 fps.
TeaCache configurable (0 = off). SageAttention con fallback automático a sdpa
(sageattention no tiene wheels Windows para este env).
Nodos: kijai ComfyUI-WanVideoWrapper (T5 + VAE + Encode + 2xLoader + 2xSampler
+ Decode + SaveImage). Sin VHS: frames -> ffmpeg en backend.

Pesos en ComfyUI/models:
  diffusion_models/high_noise/wan2.2_i2v_A14b_high_noise_lightx2v_4step-Q4_K_M.gguf
  diffusion_models/low_noise/wan2.2_i2v_A14b_low_noise_lightx2v_4step-Q4_K_M.gguf
  text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors
  vae/Wan2_2_VAE_bf16.safetensors
"""
from __future__ import annotations

import random

HIGH = "high_noise_260412\\wan2.2_i2v_A14b_high_noise_lightx2v_4step_720p_260412-Q4_K_M.gguf"
LOW = "low_noise_260412\\wan2.2_i2v_A14b_low_noise_lightx2v_4step_720p_260412-Q4_K_M.gguf"
UMT5 = "umt5-xxl-enc-fp8_e4m3fn.safetensors"
# Wan2.2 I2V usa el VAE 2.1 (latente 16ch). El VAE 2.2 (48ch) NO sirve aquí.
VAE = "Wan2_1_VAE_bf16.safetensors"

NEGATIVE_DEFAULT = (
    "low quality, worst quality, deformed, distorted, watermark, text, "
    "extra limbs, bad anatomy, static, blurry"
)

WIDTH, HEIGHT, FPS = 480, 832, 16

# FAST: 4 pasos totales (2+2), TeaCache agresivo. FINAL: 8 pasos (4+4), TeaCache 1.5.
# (La escala del doc (2.0/1.5) se mapea al rango 0-1 del nodo: 0.4/0.2.)
MODES = {
    "fast": {"steps": 4, "teacache": 0.4, "rife": False, "upscaler": "none"},
    "final": {"steps": 8, "teacache": 0.2, "rife": True, "upscaler": "anime"},
}


def _attention_mode() -> str:
    try:
        import sageattention  # noqa: F401
        import triton  # noqa: F401

        return "sageattn"
    except Exception:
        return "sdpa"


def _seconds_to_frames(seconds: float) -> int:
    # num_frames step 4 (4k+1): 2s->33, 3s->49, 4s->65, 5s->81
    frames = max(9, int(round(seconds * FPS / 4.0)) * 4 + 1)
    return min(frames, 161)


UPSCALERS = {
    "anime": "RealESRGAN_x4plus_anime_6B.pth",
    "general": "RealESRGAN_x4plus.pth",
    "none": None,
}


def build_wan_workflow(
    image_filename: str,
    prompt: str,
    negative: str = "",
    mode: str = "fast",
    seconds: float = 3.0,
    seed: int | None = None,
    teacache: float | None = None,
    blocks_to_swap: int = 24,
    upscaler: str | None = None,
    rife: bool | None = None,
) -> dict:
    if mode not in MODES:
        raise ValueError(f"mode inválido: {mode} (válidos: {sorted(MODES)})")
    cfg = MODES[mode]
    steps = cfg["steps"]
    split = steps // 2
    tc = cfg["teacache"] if teacache is None else teacache
    do_rife = cfg["rife"] if rife is None else rife
    do_up = cfg["upscaler"] if upscaler is None else upscaler
    if do_up not in UPSCALERS:
        raise ValueError(f"upscaler inválido: {do_up} (válidos: {sorted(UPSCALERS)})")
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    neg = negative.strip() or NEGATIVE_DEFAULT
    frames = _seconds_to_frames(seconds)
    attn = _attention_mode()

    wf: dict = {
        "1": {
            "class_type": "LoadWanVideoT5TextEncoder",
            "inputs": {
                "model_name": UMT5,
                "precision": "bf16",
                "load_device": "offload_device",
                "quantization": "disabled",
            },
        },
        "2": {
            "class_type": "WanVideoTextEncode",
            "inputs": {
                "positive_prompt": prompt,
                "negative_prompt": neg,
                "t5": ["1", 0],
                "force_offload": True,
                "device": "gpu",
            },
        },
        "3": {
            "class_type": "WanVideoVAELoader",
            "inputs": {"model_name": VAE, "precision": "bf16"},
        },
        "4": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename, "upload": "image"},
        },
        "5": {
            "class_type": "WanVideoImageToVideoEncode",
            "inputs": {
                "width": WIDTH,
                "height": HEIGHT,
                "num_frames": frames,
                "noise_aug_strength": 0.0,
                "start_latent_strength": 1.0,
                "end_latent_strength": 1.0,
                "force_offload": True,
                "vae": ["3", 0],
                "start_image": ["4", 0],
                "fun_or_fl2v_model": False,
                "tiled_vae": True,
            },
        },
        "10": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": HIGH,
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device",
                "attention_mode": attn,
            },
        },
        "11": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": LOW,
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device",
                "attention_mode": attn,
            },
        },
        "12": {
            "class_type": "WanVideoBlockSwap",
            "inputs": {
                "blocks_to_swap": blocks_to_swap,
                "offload_img_emb": False,
                "offload_txt_emb": False,
            },
        },
        "13": {
            "class_type": "WanVideoSetBlockSwap",
            "inputs": {"model": ["10", 0], "block_swap_args": ["12", 0]},
        },
        "14": {
            "class_type": "WanVideoSetBlockSwap",
            "inputs": {"model": ["11", 0], "block_swap_args": ["12", 0]},
        },
        "20": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["13", 0],
                "image_embeds": ["5", 0],
                "text_embeds": ["2", 0],
                "steps": steps,
                "cfg": 1.0,
                "shift": 8.0,
                "seed": seed,
                "force_offload": True,
                "scheduler": "unipc",
                "riflex_freq_index": 0,
                "start_step": 0,
                "end_step": split,
            },
        },
        "21": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["14", 0],
                "image_embeds": ["5", 0],
                "text_embeds": ["2", 0],
                "samples": ["20", 0],
                "steps": steps,
                "cfg": 1.0,
                "shift": 8.0,
                "seed": seed,
                "force_offload": True,
                "scheduler": "unipc",
                "riflex_freq_index": 0,
                "start_step": split,
                "end_step": -1,
            },
        },
        "30": {
            "class_type": "WanVideoDecode",
            "inputs": {
                "vae": ["3", 0],
                "samples": ["21", 0],
                "enable_vae_tiling": True,
                "tile_x": 272,
                "tile_y": 272,
                "tile_stride_x": 144,
                "tile_stride_y": 128,
            },
        },
        "31": {
            "class_type": "SaveImage",
            "inputs": {"images": ["30", 0], "filename_prefix": "storyforge/wan22"},
        },
    }
    images_src: str = "30"
    if do_rife:
        # RIFE x2 ANTES del upscale (más barato). 49f@16fps -> 97f.
        wf["50"] = {
            "class_type": "RIFE VFI",
            "inputs": {
                "ckpt_name": "rife49.pth",
                "frames": ["30", 0],
                "clear_cache_after_n_frames": 10,
                "multiplier": 2,
                "fast_mode": True,
                "ensemble": False,
                "scale_factor": 1.0,
                "dtype": "float32",
                "torch_compile": False,
                "batch_size": 1,
            },
        }
        images_src = "50"
    if UPSCALERS[do_up]:
        wf["51"] = {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": UPSCALERS[do_up]},
        }
        wf["52"] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["51", 0], "image": [images_src, 0]},
        }
        images_src = "52"
    wf["53"] = {
        "class_type": "SaveImage",
        "inputs": {"images": [images_src, 0], "filename_prefix": "storyforge/wan22final"},
    }
    if tc and tc > 0:
        wf["40"] = {
            "class_type": "WanVideoTeaCache",
            "inputs": {
                "rel_l1_thresh": tc,
                "start_step": 1,
                "end_step": -1,
                "cache_device": "offload_device",
                "use_coefficients": True,
            },
        }
        wf["20"]["inputs"]["cache_args"] = ["40", 0]
        wf["21"]["inputs"]["cache_args"] = ["40", 0]
    return wf
