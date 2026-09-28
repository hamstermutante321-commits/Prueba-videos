"""Render final 9:16 con FFmpeg (Phase 17, docs/08_PIPELINE_OVERVIEW.md).

Por escena: clip.mp4 (loop hasta cubrir el audio) + voice.wav + subtitles.ass
-> segmento 1080x1920 h264+aac. Luego concatena a renders/final.mp4.
Si falta clip pero hay image.png, genera un fijo de 3 s. Sin audio -> en silencio.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

OUT_W, OUT_H, FPS = 1080, 1920, 24


def _ffmpeg() -> str:
    return os.environ.get("FFMPEG_BIN", "ffmpeg")


def _ffprobe() -> str:
    return os.environ.get("FFPROBE_BIN", "ffprobe")


def _run(cmd: list[str], timeout: int = 900) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falló: {' '.join(cmd[:6])}... {proc.stderr[-600:]}")


def duration_seconds(path: Path) -> float:
    proc = subprocess.run(
        [_ffprobe(), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falló para {path}: {proc.stderr[-300:]}")
    return float(proc.stdout.strip())


def _vf(ass: Path | None) -> str:
    base = (
        f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},setsar=1,fps={FPS},format=yuv420p"
    )
    if ass and ass.exists():
        # escapar para el filtro subtitles (comillas y backslashes)
        p = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "")
        return f"{base},subtitles='{p}'"
    return base


def render_segment(sdir: Path, out_mp4: Path) -> dict:
    clip = sdir / "clip.mp4"
    image = sdir / "image.png"
    voice_wav = sdir / "voice.wav"
    ass = sdir / "subtitles.ass"
    if not clip.exists() and not image.exists():
        raise RuntimeError(f"{sdir.name}: sin clip.mp4 ni image.png")
    has_audio = voice_wav.exists()
    target = duration_seconds(voice_wav) if has_audio else None

    if clip.exists():
        video_args = ["-stream_loop", "-1", "-i", str(clip)] if target else ["-i", str(clip)]
    else:
        still_dur = target or 3.0
        video_args = [
            "-loop", "1", "-framerate", str(FPS), "-t", f"{still_dur:.2f}",
            "-i", str(image),
        ]
    cmd = [_ffmpeg(), "-y", *video_args]
    if has_audio:
        cmd += ["-i", str(voice_wav), "-shortest"]
    cmd += [
        "-vf", _vf(ass if ass.exists() else None),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    ]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
    else:
        cmd += ["-an"]
    cmd += ["-movflags", "+faststart", "-t", f"{(target or 10.0) + 0.5:.2f}" if target else "10",
            str(out_mp4)]
    # Si no hay audio, limitar a la duración del clip (máx 10 s).
    _run(cmd)
    return {"segment": out_mp4.name, "seconds": round(duration_seconds(out_mp4), 2)}


def render_project(project_dir: Path) -> dict:
    scenes_dir = project_dir / "scenes"
    scenes = sorted(p for p in scenes_dir.iterdir() if p.is_dir()) if scenes_dir.exists() else []
    if not scenes:
        raise RuntimeError("el proyecto no tiene escenas")
    renders = project_dir / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    info = []
    for sdir in scenes:
        seg = renders / f"{sdir.name}.mp4"
        info.append({"scene": sdir.name, **render_segment(sdir, seg)})
        parts.append(seg)
    lst = renders / "concat.txt"
    lst.write_text(
        "".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8"
    )
    final = renders / "final.mp4"
    _run([
        _ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-c", "copy", "-movflags", "+faststart", str(final),
    ])
    return {
        "final": str(final),
        "seconds": round(duration_seconds(final), 2),
        "segments": info,
    }
