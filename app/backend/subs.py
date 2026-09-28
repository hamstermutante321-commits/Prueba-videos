"""Subtítulos con WhisperX local (Phase 15, docs/13_SUBTITLE_SYSTEM.md).

Transcribe + alinea a nivel palabra. Descarga sus modelos a models/whisperx
(cache de HF redirigido). Carga perezosa por idioma.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_CACHE = ROOT / "models" / "whisperx"
os.environ.setdefault("HF_HUB_CACHE", str(MODEL_CACHE / "hub"))
os.environ.setdefault("XDG_CACHE_HOME", str(MODEL_CACHE))

_lock = threading.Lock()
_asr = None
_aligners: dict[str, tuple] = {}


def _load_asr(device: str = "cuda", compute_type: str = "float16"):
    global _asr
    with _lock:
        if _asr is None:
            import whisperx

            _asr = whisperx.load_model(
                "large-v2", device=device, compute_type=compute_type
            )
        return _asr


def _load_aligner(language: str, device: str = "cuda"):
    if language not in _aligners:
        import whisperx

        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=device
        )
        _aligners[language] = (model_a, metadata)
    return _aligners[language]


def transcribe_words(audio_path: Path, language: str = "es") -> dict:
    """Devuelve {'segments': [...], 'words': [{word, start, end, score}]}."""
    import torch
    import whisperx

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    audio = whisperx.load_audio(str(audio_path))
    asr = _load_asr(device, compute)
    result = asr.transcribe(audio, batch_size=8, language=language)
    if not result.get("segments"):
        raise RuntimeError("WhisperX no detectó habla en el audio")
    model_a, metadata = _load_aligner(language, device)
    aligned = whisperx.align(
        result["segments"], model_a, metadata, audio, device,
        return_char_alignments=False,
    )
    words = []
    for seg in aligned.get("segments", []):
        for w in seg.get("words", []):
            if "start" in w and "end" in w:
                words.append(
                    {
                        "word": str(w.get("word", "")).strip(),
                        "start": round(float(w["start"]), 3),
                        "end": round(float(w["end"]), 3),
                        "score": round(float(w.get("score", 0.0)), 3),
                    }
                )
    if not words:
        raise RuntimeError("WhisperX no pudo alinear palabras")
    return {
        "language": language,
        "segments": [
            {
                "start": s.get("start"),
                "end": s.get("end"),
                "text": s.get("text", ""),
            }
            for s in aligned.get("segments", [])
        ],
        "words": words,
    }
