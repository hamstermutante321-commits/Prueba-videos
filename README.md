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
Ollama (ideas) · ComfyUI + SDXL / FLUX (imagen) · **CogVideoX-5B-I2V (image-to-video principal)** ·
FramePack (alternativa secundaria) · LTX-Video (deprecated) ·
XTTS v2 (voz) · WhisperX (subtítulos) · FFmpeg (render) · React+Vite + FastAPI

## Image-to-video (cambio_IA.md)

| Backend | Rol | Notas |
|---|---|---|
| `cogvideox_i2v` | **Principal (default)** | GGUF Q4 + offload: corre en 8 GB VRAM. 480x720 @ 8 fps, vertical directo. Mejor fidelidad y seguimiento del prompt. |
| `framepack` | Secundario | Videos más largos / continuidad. Prompts cortos de movimiento. Pesos (~30 GB) pendientes. |
| `ltx` | Deprecated | Se mantiene funcional. Distorsiona y sigue mal el motion prompt. |

Endpoint: `POST /api/projects/{id}/scenes/{sid}/video` con `{"motion_prompt", "preset", "backend"}`.
Backends: `GET /api/system/video-backends` (default `cogvideox_i2v`, ver `app/backend/video_backends.py`).

### Regla de prompting I2V (motion-only)
- El **image prompt** describe la escena completa.
- El **motion prompt** describe SOLO la animación: movimiento del sujeto, movimiento
  secundario del entorno, movimiento de cámara + 1 restricción de continuidad
  (`same face, same clothes, no morphing`). NO repite la descripción de la imagen.

## Notas de entorno (fijadas con sangre)
- `transformers==4.57.6` (5.x rompe coqui-tts) · `diffusers==0.34.0` + `huggingface_hub==0.36.2`
  (el wrapper CogVideoX no importa con hub 1.x/2.x y diffusers 0.40).
- `requirements-gpu.txt` primero si CUDA desaparece (algún pip reemplaza torch-cu126 por CPU).
- DLLs FFmpeg shared en `tools/ffmpeg-shared/` para torchcodec (no se suben a git).

## Política de ramas
Todo va a `main`. Sin ramas, sin PRs internos.

## Estado
Phase 0 en curso: preflight + GitHub setup.
