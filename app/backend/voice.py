"""Voz y narración con Coqui XTTS v2 local (Phase 14, docs/12).

- Referencia: mp4/mp3/wav/m4a -> ffmpeg extrae wav mono 24kHz.
- Narración: XTTS tts_to_file con speaker_wav de referencia.
- Modelo en models/xtts-v2 (no se sube a git). Carga perezosa, una vez por proceso.
"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "xtts-v2"

# torchcodec (vía torchaudio/Coqui) necesita los DLLs compartidos de FFmpeg.
# Están en tools/ffmpeg-shared (no se suben a git).
_FF_SHARED = ROOT / "tools" / "ffmpeg-shared"
if _FF_SHARED.exists() and str(_FF_SHARED) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_FF_SHARED) + os.pathsep + os.environ.get("PATH", "")
REQUIRED_FILES = (
    "model.pth",
    "config.json",
    "vocab.json",
    "speakers_xtts.pth",
    "mel_stats.pth",
    "dvae.pth",
)

_lock = threading.Lock()
_tts = None


def model_ready() -> tuple[bool, list[str]]:
    missing = [f for f in REQUIRED_FILES if not (MODEL_DIR / f).exists()]
    return (len(missing) == 0, missing)


def _ffmpeg() -> str:
    return os.environ.get("FFMPEG_BIN", "ffmpeg")


def extract_reference(src: Path, dst_wav: Path, start: float = 0.0, seconds: float = 20.0) -> dict:
    """Extrae un tramo de audio de referencia a wav mono 24kHz 16-bit."""
    dst_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg(), "-y",
        "-ss", str(start),
        "-i", str(src),
        "-t", str(seconds),
        "-ac", "1", "-ar", "24000", "-sample_fmt", "s16",
        str(dst_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0 or not dst_wav.exists():
        raise RuntimeError(f"ffmpeg no pudo extraer el audio: {proc.stderr[-500:]}")
    return {"reference_wav": str(dst_wav), "bytes": dst_wav.stat().st_size}


def _get_tts():
    global _tts
    with _lock:
        if _tts is None:
            ok, missing = model_ready()
            if not ok:
                raise RuntimeError(f"faltan pesos XTTS en models/xtts-v2: {missing}")
            from TTS.api import TTS

            _tts = TTS(
                model_path=str(MODEL_DIR),
                config_path=str(MODEL_DIR / "config.json"),
                progress_bar=False,
            ).to("cuda" if _cuda_available() else "cpu")
        return _tts


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def synthesize(text: str, speaker_wav: Path, out_wav: Path, language: str = "es") -> dict:
    """Genera narración con la voz de referencia."""
    text = text.strip()
    if not text:
        raise RuntimeError("texto vacío: nada que narrar")
    if not speaker_wav.exists():
        raise RuntimeError("no hay voz de referencia: súbela primero")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tts = _get_tts()
    with _lock:
        tts.tts_to_file(
            text=text,
            speaker_wav=str(speaker_wav),
            language=language,
            file_path=str(out_wav),
        )
    if not out_wav.exists():
        raise RuntimeError("XTTS no generó el wav")
    return {"wav": str(out_wav), "bytes": out_wav.stat().st_size}
