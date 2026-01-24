import os
import json
import random
from typing import List, Optional, Dict, Any

import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920


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
    arr = np.array(pil_rgba)  # H,W,4
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3] / 255.0
    clip = ImageClip(rgb)
    mask = ImageClip(alpha, ismask=True)
    return clip.set_mask(mask)


def _wrap_words(draw: ImageDraw.ImageDraw, words: List[str], font: ImageFont.ImageFont, max_width: int) -> List[List[str]]:
    lines: List[List[str]] = []
    cur: List[str] = []

    for w in words:
        test = cur + [w]
        test_text = " ".join(test)
        bbox = draw.textbbox((0, 0), test_text, font=font)
        tw = bbox[2] - bbox[0]
        if tw <= max_width or not cur:
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

    clean = [_sanitize(w).upper() for w in words if w and w.strip()]
    if not clean:
        return img

    lines = _wrap_words(draw, clean, font, max_width=max_width)

    line_h = 95
    total_h = len(lines) * line_h
    y0 = int(H * y_ratio) - total_h // 2

    idx_global = 0
    for li, line_words in enumerate(lines):
        line_text = " ".join(line_words)
        bbox = draw.textbbox((0, 0), line_text, font=font)
        tw = bbox[2] - bbox[0]
        x = int((W - tw) / 2)
        y = y0 + li * line_h

        # borde + blanco
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox == 0 and oy == 0:
                    continue
                draw.text((x + ox, y + oy), line_text, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line_text, font=font, fill=(255, 255, 255, 255))

        # overlay verde palabra activa
        cx = x
        for wi, w in enumerate(line_words):
            prefix = "" if wi == 0 else " "
            pxw = draw.textbbox((0, 0), prefix, font=font)[2]
            cx += pxw

            ww = draw.textbbox((0, 0), w, font=font)[2]
            if idx_global == active_idx:
                for ox in range(-stroke, stroke + 1):
                    for oy in range(-stroke, stroke + 1):
                        if ox == 0 and oy == 0:
                            continue
                        draw.text((cx + ox, y + oy), w, font=font, fill=(0, 0, 0, 255))
                draw.text((cx, y), w, font=font, fill=(0, 255, 0, 255))

            cx += ww
            idx_global += 1

    return img


def _normalize_word_timings(meta: Dict[str, Any], audio_dur: float) -> List[Dict[str, Any]]:
    """
    Soporta:
    - meta["words"] con start/end
    - meta["raw_words"] con offset_raw/duration_raw
    Auto detecta escala: 100ns vs ms vs s.
    Permite ajuste global SUB_SHIFT (en segundos).
    """
    if not isinstance(meta, dict):
        return []

    # caso normalizado
    if "words" in meta and meta["words"]:
        w0 = meta["words"][0]
        if isinstance(w0, dict) and ("start" in w0 and "end" in w0 and "word" in w0):
            words = meta["words"]
        else:
            words = []
    else:
        words = []

    # caso raw
    if not words:
        raw = meta.get("raw_words", [])
        if not raw:
            return []

        offsets = [float(x.get("offset_raw", x.get("offset", 0))) for x in raw]
        durs = [float(x.get("duration_raw", x.get("duration", 0))) for x in raw]
        max_off = max(offsets) if offsets else 0.0

        candidates = {"100ns": 10_000_000.0, "ms": 1000.0, "s": 1.0}
        best_div = 10_000_000.0
        best_err = float("inf")

        for _, div in candidates.items():
            last_t = max_off / div
            err = abs(last_t - audio_dur)
            if err < best_err:
                best_err = err
                best_div = div

        words = []
        for x, off, du in zip(raw, offsets, durs):
            start = off / best_div
            dur = (du / best_div) if du > 0 else 0.18
            end = start + dur
            w = (x.get("word") or x.get("text") or "").strip()
            if w:
                words.append({"word": w, "start": float(start), "end": float(end)})

    # shift global por delay mp3 (ajustable sin tocar código)
    shift = float(os.getenv("SUB_SHIFT", "0.0"))
    if shift != 0.0:
        for w in words:
            w["start"] = max(0.0, w["start"] + shift)
            w["end"] = max(w["start"] + 0.05, w["end"] + shift)

    # limpieza de rangos
    out = []
    for w in words:
        s = float(w.get("start", 0.0))
        e = float(w.get("end", s + 0.18))
        if e <= s:
            e = s + 0.18
        if s <= audio_dur:
            out.append({"word": str(w.get("word", "")).strip(), "start": s, "end": min(e, audio_dur)})
    return [x for x in out if x["word"]]


def render_short(
    audio_path: str,
    title: str,          # se ignora
    script_text: str,    # solo fallback
    out_path: str,
    topic_hint: str = "",
    meta_path: Optional[str] = None
):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    bg_path = _pick_background(topic_hint)
    base = ImageClip(bg_path).resize((W, H))
    base = _ken_burns(base, dur)

    overlays: List[ImageClip] = []

    # 1) Cargar timings palabra por palabra
    words = []
    if meta_path and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        words = meta.get("words", [])

    # 2) Si NO hay timings (no debería pasar)
    if not words:
        st = _sanitize(script_text).upper().strip()
        if st:
            frame = _draw_subtitle_frame(st.split(), active_idx=-1, y_ratio=0.74)
            overlays.append(
                _rgba_clip(frame)
                .set_start(0)
                .set_duration(dur)
            )
    else:
        # 3) Ajuste opcional por delay de MP3
        shift = float(os.getenv("SUB_SHIFT", "0.0"))
        if shift != 0.0:
            for w in words:
                w["start"] = max(0.0, float(w["start"]) + shift)
                w["end"] = max(w["start"] + 0.05, float(w["end"]) + shift)

        # 4) Karaoke: ventana de palabras
        window = int(os.getenv("SUB_WINDOW", "12"))

        for i, w in enumerate(words):
            start = float(w["start"])
            end = float(w["end"])

            if end <= start or start >= dur:
                continue

            lo = max(0, i - (window - 1))
            chunk_words = [x["word"] for x in words[lo:i + 1] if x.get("word")]

            active = len(chunk_words) - 1

            frame = _draw_subtitle_frame(
                chunk_words,
                active_idx=active,
                y_ratio=0.74
            )

            overlays.append(
                _rgba_clip(frame)
                .set_start(start)
                .set_duration(min(end - start, dur - start))
            )

    final = CompositeVideoClip([base, *overlays], size=(W, H)).set_audio(audio)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
