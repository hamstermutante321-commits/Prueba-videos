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
