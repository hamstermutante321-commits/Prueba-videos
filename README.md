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
Ollama (ideas) · ComfyUI + SDXL / FLUX (imagen) · LTX-Video (image-to-video) ·
XTTS v2 (voz) · WhisperX (subtítulos) · FFmpeg (render) · React+Vite + FastAPI

## Política de ramas
Todo va a `main`. Sin ramas, sin PRs internos.

## Estado
Phase 0 en curso: preflight + GitHub setup.
