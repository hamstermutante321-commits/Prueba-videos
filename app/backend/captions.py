"""Bloques de subtítulos + ASS 9:16 (Phase 16, docs/13_SUBTITLE_SYSTEM.md).

Agrupa palabras en bloques legibles (2 líneas, ~24 cars/línea) y genera
ASS con estilos para lienzo vertical. Sin dependencias extra.
"""
from __future__ import annotations


def build_blocks(
    words: list[dict],
    max_chars_per_line: int = 24,
    max_lines: int = 2,
    max_words: int = 8,
    max_gap: float = 0.6,
) -> list[dict]:
    """Agrupa palabras en bloques. Pausa larga o límites -> bloque nuevo."""
    blocks: list[dict] = []
    lines: list[str] = []
    cur: list[dict] = []

    def flush() -> None:
        if not cur:
            return
        text = "\n".join(lines) if lines else " ".join(w["word"] for w in cur)
        blocks.append(
            {
                "text": text,
                "start": cur[0]["start"],
                "end": cur[-1]["end"],
                "line_count": max(1, len(lines) if lines else 1),
            }
        )

    def fits_line(word: str) -> bool:
        current = lines[-1] if lines else ""
        candidate = f"{current} {word}".strip()
        return len(candidate) <= max_chars_per_line

    for i, w in enumerate(words):
        prev = words[i - 1] if i else None
        gap = w["start"] - prev["end"] if prev else 0.0
        if cur and (gap >= max_gap or len(cur) >= max_words):
            flush()
            lines, cur = [], []
        if not cur:
            lines, cur = [w["word"]], [w]
            continue
        if len(lines) >= max_lines and not fits_line(w["word"]):
            flush()
            lines, cur = [w["word"]], [w]
            continue
        if fits_line(w["word"]):
            lines[-1] = f"{lines[-1]} {w['word']}".strip()
        elif len(lines) < max_lines:
            lines.append(w["word"])
        else:
            flush()
            lines = [w["word"]]
            cur = []
        cur.append(w)
    flush()
    return blocks


STYLES = {
    "classic": {
        "Fontname": "Arial",
        "Fontsize": 64,
        "Bold": 0,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H99000000",
        "BackColour": "&H99000000",
        "BorderStyle": 1,
        "Outline": 2,
        "Shadow": 0,
        "Alignment": 2,
    },
    "bold social": {
        "Fontname": "Arial Black",
        "Fontsize": 72,
        "Bold": -1,
        "PrimaryColour": "&H0000FFFF",
        "OutlineColour": "&H99000000",
        "BackColour": "&H99000000",
        "BorderStyle": 1,
        "Outline": 3,
        "Shadow": 0,
        "Alignment": 2,
    },
    "karaoke highlight": {
        "Fontname": "Arial",
        "Fontsize": 64,
        "Bold": -1,
        "PrimaryColour": "&H00B4B4B4",
        "SecondaryColour": "&H0000FFFF",
        "OutlineColour": "&H99000000",
        "BackColour": "&H99000000",
        "BorderStyle": 1,
        "Outline": 2,
        "Shadow": 0,
        "Alignment": 2,
    },
    "minimal": {
        "Fontname": "Arial",
        "Fontsize": 52,
        "Bold": 0,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&HCC000000",
        "BackColour": "&HCC000000",
        "BorderStyle": 1,
        "Outline": 1,
        "Shadow": 0,
        "Alignment": 2,
    },
}


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _karaoke_line(block: dict, words: list[dict]) -> str:
    """Línea con tags \\k por palabra (tiempos relativos al bloque en centiseg)."""
    parts: list[str] = []
    for w in words:
        if w["end"] <= block["start"] or w["start"] >= block["end"]:
            continue
        dur_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
        parts.append(f"{{\\k{dur_cs}}}{w['word']}")
    return " ".join(parts)


def blocks_to_ass(
    blocks: list[dict],
    words: list[dict] | None = None,
    style: str = "classic",
    play_w: int = 1080,
    play_h: int = 1920,
    margin_v: int = 320,
    font_scale: float = 1.0,
) -> str:
    """Genera el contenido .ass. margin_v sube los subtítulos a la zona segura."""
    if style not in STYLES:
        raise ValueError(f"estilo inválido: {style} (válidos: {sorted(STYLES)})")
    st = dict(STYLES[style])
    st["Fontsize"] = int(st["Fontsize"] * font_scale)
    st["MarginV"] = margin_v
    st["MarginL"] = 60
    st["MarginR"] = 60

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {play_w}\n"
        f"PlayResY: {play_h}\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n"
        "\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,{Fontname},{Fontsize},{PrimaryColour},{SecondaryColour},"
        "{OutlineColour},{BackColour},{Bold},0,0,0,100,100,0,0,{BorderStyle},"
        "{Outline},{Shadow},{Alignment},{MarginL},{MarginR},{MarginV},1\n"
        "\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    ).format(
        **{k: st.get(k, "&H00000000" if "Colour" in k else 0) for k in (
            "Fontname", "Fontsize", "PrimaryColour", "SecondaryColour",
            "OutlineColour", "BackColour", "Bold", "BorderStyle", "Outline",
            "Shadow", "Alignment", "MarginL", "MarginR", "MarginV",
        )}
    )
    lines = [header]
    for b in blocks:
        if style == "karaoke highlight" and words:
            text = _karaoke_line(b, words).replace("\n", "\\N")
        else:
            text = b["text"].replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_ass_time(b['start'])},{_ass_time(b['end'])},"
            f"Default,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"
