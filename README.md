# Prueba-videos — Local AI Story Pipeline

Repo de proyecto para **StoryForge Local Studio**: app local que genera mini-historias verticales 9:16
(idea → escenas → imagen → video → voz clonada → subtítulos → render final).

## Raíz de trabajo
`%USERPROFILE%\Downloads\LocalAIStoryPipeline\`

```
app/        código frontend + backend
projects/   proyectos (project.json, story_plan.json, scenes/...)
models/     modelos locales (no se suben a git)
outputs/    renders finales
temp/       temporales
logs/       logs
```

## Hardware objetivo
Ryzen 5 7600X · RTX 4060 Ti 8GB · 32GB RAM DDR5

## Stack
Ollama (ideas) · ComfyUI + SDXL / FLUX (imagen) · **Wan 2.2 I2V-A14B + LightX2V 4-step (image-to-video principal)** ·
CogVideoX-5B-I2V (secundario) · FramePack (alternativa, pesos pendientes) · LTX-Video (deprecated, sin pesos) ·
XTTS v2 (voz) · WhisperX (subtítulos) · FFmpeg (render) · React+Vite + FastAPI

## Image-to-video: Wan 2.2 I2V-A14B + LightX2V 4-step (principal)

Pipeline: imagen → preproceso 9:16 → Wan dual HIGH/LOW (Q4_K_M GGUF) → base 480x832@16fps
→ RIFE x2 (FINAL) → Real-ESRGAN x4 (FINAL) → FFmpeg → 1080x1920 H.264.

| Backend | Rol | Notas |
|---|---|---|
| `wan_i2v` | **Principal (default)** | Q4_K_M + TeaCache + block-swap 24: corre en 8 GB VRAM. Modos FAST (solo base) y FINAL (RIFE+ESRGAN). |
| `cogvideox_i2v` | Secundario | GGUF Q4, 480x720@8fps vertical. |
| `framepack` | Secundario | Videos más largos / continuidad. Prompts cortos. Pesos (~30 GB) pendientes. |
| `ltx` | Deprecated | Pesos borrados para hacer sitio. Solo queda el código. |

Endpoint: `POST /api/projects/{id}/scenes/{sid}/video` con
`{motion_prompt, backend, mode(fast|final), seconds, seed, teacache, interpolate, upscaler(anime|general|none), out_fps}`.
Backends: `GET /api/system/video-backends` (ver `app/backend/video_backends.py`).

Pesos Wan en `ComfyUI/models`: `diffusion_models/high_noise_260412/*Q4_K_M.gguf`,
`diffusion_models/low_noise_260412/*Q4_K_M.gguf`, `text_encoders/umt5-xxl-enc-fp8_e4m3fn`,
`vae/Wan2_1_VAE_bf16` (el VAE 2.2 da 48ch y NO sirve: el transformer espera 36ch).

### Decisiones documentadas (alternativas compatibles)
- **SageAttention/Sage2**: sin wheels Windows para py3.11+cu126 (sageattn 1.0.6 pide
  triton, ausente). Fallback automático a `sdpa`. El adapter lo intenta y si falla usa sdpa.
- **TeaCache**: nodo `WanVideoTeaCache` con `rel_l1_thresh` 0-1 (FAST 0.4 / FINAL 0.2;
  la escala 1.5/2.0 del doc no existe en el nodo). Coeficientes Wan2.2 pendientes en el
  wrapper (usa placeholder); si mete artefactos, TeaCache off.
- **realesr-general-x4v3 / AnimeVideo-v3**: no publicados en mirror accesible; se usa
  `RealESRGAN_x4plus` (general) y `RealESRGAN_x4plus_anime_6B` (anime).
- **RIFE-vía-ComfyUI**: requiere CUDA toolkit para su install.py; se usa el nodo
  `RIFE VFI` (torch puro, rife49.pth) dentro del grafo ComfyUI.
- **torch.compile**: no activado (riesgo de VRAM/estabilidad en 8 GB; TeaCache+4-step
  ya dan el salto).

### Regla de prompting I2V (motion-only)
- El **image prompt** describe la escena completa.
- El **motion prompt** describe SOLO la animación: movimiento del sujeto, movimiento
  secundario del entorno, movimiento de cámara + 1 restricción de continuidad
  (`same face, same clothes, no morphing`). NO repite la descripción de la imagen.

## Notas de entorno (fijadas con sangre)
- `transformers==4.57.6` (5.x rompe coqui-tts) · `diffusers==0.34.0` + `huggingface_hub==0.36.2`
  (los wrappers no importan con hub 1.x/2.x y diffusers 0.40).
- `requirements-gpu.txt` primero si CUDA desaparece (algún pip reemplaza torch-cu126 por CPU).
- DLLs FFmpeg shared en `tools/ffmpeg-shared/` para torchcodec (no se suben a git).
- `sageattention` 1.0.6 pide `triton` (ausente en Windows) → adapter Wan usa `sdpa`.

## Política de ramas
Todo va a `main`. Sin ramas, sin PRs internos.

## Estado
MVP completo hasta Phase 20 + migración I2V a Wan 2.2 (principal). Ver `outputs/mvp_final.mp4` y `outputs/wan_final.mp4`.
