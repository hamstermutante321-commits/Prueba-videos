"""Adapter de Ollama para expansión de ideas (docs/09_IDEA_EXPANSION_ENGINE.md).

Usa solo stdlib (urllib). Modelo configurable con env OLLAMA_MODEL.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

IDEA_JSON_SHAPE = (
    '{"ideas": [{"title": "...", "summary": "...", "hook": "...", '
    '"conflict": "...", "cliffhanger": "..."}]}'
)


def _call_generate(prompt: str, temperature: float = 0.7, timeout: int = 300) -> dict:
    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
    }
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Ollama no responde en {OLLAMA_HOST}. "
            f"Verifica que Ollama esté corriendo (ollama list). Detalle: {exc}"
        ) from exc
    try:
        payload = json.loads(raw)
        return json.loads(payload["response"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama devolvió JSON inválido: {raw[:300]}") from exc


def generate_root_ideas(idea: str, style: str, count: int) -> list[dict]:
    prompt = (
        "Eres un guionista de mini-historias verticales (shorts/reels).\n"
        f"Idea libre del usuario: {idea}\n"
        f"Estilo visual deseado: {style}\n"
        f"Genera {count} ideas principales ALTERNATIVAS y distintas entre sí, "
        "cada una con título, resumen (2-3 frases), hook inicial (primera frase que engancha), "
        "conflicto central y cliffhanger final.\n"
        "Responde SOLO con este JSON, sin texto extra: " + IDEA_JSON_SHAPE
    )
    data = _call_generate(prompt)
    return _as_list(data)


def generate_child_ideas(branch_path: list[dict], count: int) -> list[dict]:
    path_text = "\n".join(
        f"Nivel {i}: {n.get('title', '')} — {n.get('summary', '')}"
        for i, n in enumerate(branch_path)
    )
    current = branch_path[-1] if branch_path else {}
    prompt = (
        "Eres un guionista de mini-historias verticales (shorts/reels).\n"
        "Esta es la rama narrativa elegida (raíz -> ... -> nodo actual):\n"
        f"{path_text}\n"
        f"Genera {count} subideas HIJAS que continúen EXACTAMENTE desde "
        f"el nodo actual ('{current.get('title', '')}'), sin reiniciar la historia. "
        "Cada una con título, resumen (2-3 frases), hook, conflicto y cliffhanger.\n"
        "Responde SOLO con este JSON, sin texto extra: " + IDEA_JSON_SHAPE
    )
    data = _call_generate(prompt)
    return _as_list(data)


def _as_list(data: dict) -> list[dict]:
    ideas = data.get("ideas", [])
    if not isinstance(ideas, list) or not ideas:
        raise RuntimeError(f"Ollama no devolvió ideas: {str(data)[:300]}")
    norm = []
    for item in ideas:
        if not isinstance(item, dict):
            continue
        norm.append(
            {
                "title": str(item.get("title", "")).strip()[:200],
                "summary": str(item.get("summary", "")).strip(),
                "hook": str(item.get("hook", "")).strip(),
                "conflict": str(item.get("conflict", "")).strip(),
                "cliffhanger": str(item.get("cliffhanger", "")).strip(),
            }
        )
    if not norm:
        raise RuntimeError("Ollama devolvió ideas vacías")
    return norm


STORY_JSON_SHAPE = (
    '{"hook": "...", "summary": "...", "cliffhanger": "...", '
    '"scenes": [{"title": "...", "purpose": "...", "duration_seconds": 8, '
    '"image_prompt": "...", "motion_prompt": "...", "narration": "...", '
    '"subtitle_text": "...", "transition_note": "...", "continuity_notes": "..."}]}'
)


def _parse_story(data: dict, scene_count: int) -> dict:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        raise RuntimeError(f"Ollama no devolvió escenas: {str(data)[:300]}")
    norm = []
    for i, item in enumerate(scenes[:scene_count]):
        if not isinstance(item, dict):
            continue
        try:
            duration = int(item.get("duration_seconds", 8))
        except (TypeError, ValueError):
            duration = 8
        norm.append(
            {
                "title": str(item.get("title", f"Escena {i + 1}")).strip()[:200],
                "purpose": str(item.get("purpose", "")).strip(),
                "duration_seconds": max(2, min(15, duration)),
                "image_prompt": str(item.get("image_prompt", "")).strip(),
                "motion_prompt": str(item.get("motion_prompt", "")).strip(),
                "narration": str(item.get("narration", "")).strip(),
                "subtitle_text": str(item.get("subtitle_text", "")).strip(),
                "transition_note": str(item.get("transition_note", "")).strip(),
                "continuity_notes": str(item.get("continuity_notes", "")).strip(),
            }
        )
    if not norm:
        raise RuntimeError("Ollama devolvió escenas vacías")
    return {
        "hook": str(data.get("hook", "")).strip(),
        "summary": str(data.get("summary", "")).strip(),
        "cliffhanger": str(data.get("cliffhanger", "")).strip(),
        "scenes": norm,
    }


def _branch_text(branch_path: list[dict]) -> str:
    return "\n".join(
        f"Nivel {i}: {n.get('title', '')} — {n.get('summary', '')} "
        f"(conflicto: {n.get('conflict', '')})"
        for i, n in enumerate(branch_path)
    )


def generate_story(branch_path: list[dict], scene_count: int, style: str) -> dict:
    prompt = (
        "Eres un guionista de mini-historias verticales 9:16 (shorts/reels).\n"
        "Rama narrativa elegida (raíz -> ... -> nodo final):\n"
        f"{_branch_text(branch_path)}\n"
        f"Convierte esta rama en una historia SECUENCIAL de {scene_count} escenas "
        f"para estilo visual '{style}', con hook fuerte en la escena 1 y "
        "cliffhanger en la última.\n"
        "Cada escena necesita: title, purpose, duration_seconds (4-10), "
        "image_prompt (EN INGLÉS, detallado, vertical 9:16, incluye el estilo), "
        "motion_prompt (EN INGLÉS, movimiento de cámara/acción sutil), "
        "narration (ESPAÑOL, 1-2 frases para voz en off), "
        "subtitle_text (ESPAÑOL, versión corta de la narración), "
        "transition_note y continuity_notes (personajes, objetos y hechos que "
        "deben mantenerse entre escenas).\n"
        "Responde SOLO con este JSON, sin texto extra: " + STORY_JSON_SHAPE
    )
    return _parse_story(_call_generate(prompt, temperature=0.7), scene_count)


def generate_more_scenes(
    branch_path: list[dict],
    existing: list[dict],
    extra_count: int,
    style: str,
) -> dict:
    existing_text = "\n".join(
        f"Escena {i + 1}: {s.get('title', '')} — {s.get('purpose', '')}"
        for i, s in enumerate(existing)
    )
    prompt = (
        "Eres un guionista de mini-historias verticales 9:16.\n"
        f"Rama narrativa: {_branch_text(branch_path)}\n"
        "Escenas ya materializadas (NO las repitas, continúa DESPUÉS de la última, "
        "manteniendo personajes, hechos, tono y conflictos abiertos):\n"
        f"{existing_text}\n"
        f"Genera {extra_count} escenas NUEVAS que continúen la historia, estilo "
        f"'{style}', con el mismo formato de campos que antes "
        "(image_prompt y motion_prompt EN INGLÉS, narration y subtitle_text EN ESPAÑOL).\n"
        "Responde SOLO con este JSON, sin texto extra: " + STORY_JSON_SHAPE
    )
    return _parse_story(_call_generate(prompt, temperature=0.7), extra_count)
