import os
import json
import random
from typing import List, Optional, Dict, Any

import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
TICKS_PER_SECOND = 10_000_000  # edge-tts usa 100ns


# ----------------- UTILIDADES -----------------

def _font(size=86):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _sanitize(s: str) -> str:
    if not s:
        return ""
    return (
        s.replace("\u2019", "'")
         .replace("\u2018", "'")
         .replace("\u201C", '"')
         .replace("\u201D", '"')
         .replace("\u2014", "-")
         .replace("\u2013", "-")
         .replace("\u2026", "...")
    )


def _pick_background(topic_hint: str) -> str:
    root = "assets/backgrounds"
    if not os.path.isdir(root):
        raise RuntimeError("Missing assets/backgrounds folder")

    hint = (topic_hint or "").lower()
    keyword_map = {
        "space": ["space", "planet", "universe", "galaxy", "star", "moon", "cosmos"],
        "money": ["money", "rich", "poor", "wealth", "broke", "income", "salary", "debt"],
        "mindset": ["mindset", "discipline", "focus", "fear", "confidence", "habit", "comfort", "truth"],
        "relationships": ["love", "friends", "relationship", "alone", "people"],
    }

    chosen_folder = None
    for folder, kws in keyword_map.items():
        if any(k in hint for k in kws) and os.path.isdir(os.path.join(root, folder)):
            chosen_folder = os.path.join(root, folder)
            break

    if chosen_folder is None:
        chosen_folder = os.path.join(root, "general") if os.path.isdir(os.path.join(root, "general")) else root

    files = [
        os.path.join(chosen_folder, fn)
        for fn in os.listdir(chosen_folder)
        if fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]
    if not files:
        raise RuntimeError(f"No images found in {chosen_folder}")

    return random.choice(files)


def _ken_burns(clip: ImageClip, duration: float) -> ImageClip:
    def zoom(t):
        return 1.00 + 0.03 * (t / max(duration, 0.001))

    max_dx = 40
    max_dy = 60

    def pos(t):
        p = t / max(duration, 0.001)
        dx = int((p - 0.5) * 2 * max_dx)
        dy = int((0.5 - p) * 2 * max_dy)
        return (dx, dy)

    return clip.set_duration(duration).resize(zoom).set_position(pos)


def _rgba_clip(pil_rgba: Image.Image) -> ImageClip:
    arr = np.array(pil_rgba)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3] / 255.0
    clip = ImageClip(rgb)
    mask = ImageClip(alpha, ismask=True)
    return clip.set_mask(mask)


# ----------------- TEXTO -----------------

def _wrap_words(draw, words, font, max_width):
    lines, cur = [], []
    for w in words:
        test = cur + [w]
        if draw.textbbox((0, 0), " ".join(test), font=font)[2] <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = [w]
    if cur:
        lines.append(cur)
    return lines[:2]


def _draw_subtitle_frame(words: List[str], active_idx: int, y_ratio: float = 0.74) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = _font(74)
    stroke = 6
    max_width = int(W * 0.88)

    clean = [_sanitize(w).upper() for w in words if w.strip()]
    if not clean:
        return img

    lines = _wrap_words(draw, clean, font, max_width)
    line_h = 95
    y0 = int(H * y_ratio) - (len(lines) * line_h) // 2

    idx = 0
    for li, line_words in enumerate(lines):
        text = " ".join(line_words)
        tw = draw.textbbox((0, 0), text, font=font)[2]
        x = (W - tw) // 2
        y = y0 + li * line_h

        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox or oy:
                    draw.text((x + ox, y + oy), text, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        cx = x
        for w in line_words:
            pw = draw.textbbox((0, 0), " ", font=font)[2] if cx != x else 0
            cx += pw
            ww = draw.textbbox((0, 0), w, font=font)[2]
            if idx == active_idx:
                for ox in range(-stroke, stroke + 1):
                    for oy in range(-stroke, stroke + 1):
                        if ox or oy:
                            draw.text((cx + ox, y + oy), w, font=font, fill=(0, 0, 0, 255))
                draw.text((cx, y), w, font=font, fill=(0, 255, 0, 255))
            cx += ww
            idx += 1

    return img


# ----------------- TIMINGS -----------------

def _normalize_word_timings(meta: Dict[str, Any], audio_dur: float) -> List[Dict[str, Any]]:
    words = meta.get("words", [])
    if not words:
        raw = meta.get("raw_words", [])
        for r in raw:
            start = r["offset_raw"] / TICKS_PER_SECOND
            end = (r["offset_raw"] + r["duration_raw"]) / TICKS_PER_SECOND
            if end <= start:
                end = start + 0.1
            words.append({"word": r["word"], "start": start, "end": end})

    shift = float(os.getenv("SUB_SHIFT", "0.0"))
    out = []
    for w in words:
        s = max(0.0, w["start"] + shift)
        e = max(s + 0.1, w["end"] + shift)
        if s <= audio_dur:
            out.append({"word": w["word"], "start": s, "end": min(e, audio_dur)})
    return out


# ----------------- RENDER -----------------

def render_short(
    audio_path: str,
    title: str,        # ignorado
    script_text: str,  # ignorado
    out_path: str,
    topic_hint: str = "",
    meta_path: Optional[str] = None
):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    base = ImageClip(_pick_background(topic_hint)).resize((W, H))
    base = _ken_burns(base, dur)

    overlays = []

    # --- Cargar y normalizar metadata ---
    if not meta_path or not os.path.exists(meta_path):
        raise RuntimeError("meta_path no existe – no hay subtítulos")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    words = _normalize_word_timings(meta, audio_dur=dur)

    if not words:
        raise RuntimeError("No se pudieron normalizar palabras")

    # --- Parámetros ESTABLES ---
    WINDOW = int(os.getenv("SUB_WINDOW", "8"))       # menos palabras = más legible
    MIN_WORD_DUR = float(os.getenv("MIN_WORD_DUR", "0.18"))  # 👈 CLAVE
    Y_RATIO = float(os.getenv("SUB_Y", "0.74"))

    for i, w in enumerate(words):
        start = float(w["start"])
        end = float(w["end"])

        # clamp fuerte
        if end - start < MIN_WORD_DUR:
            end = start + MIN_WORD_DUR

        if start >= dur:
            break

        lo = max(0, i - WINDOW + 1)
        chunk_words = [x["word"] for x in words[lo:i + 1]]
        active_idx = len(chunk_words) - 1

        frame = _draw_subtitle_frame(
            chunk_words,
            active_idx=active_idx,
            y_ratio=Y_RATIO
        )

        overlays.append(
            _rgba_clip(frame)
            .set_start(start)
            .set_duration(min(end - start, dur - start))
        )

    final = CompositeVideoClip(
        [base, *overlays],
        size=(W, H)
    ).set_audio(audio)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium"
    )
