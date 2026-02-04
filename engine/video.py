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
    """
    Intenta obtener timings palabra-por-palabra.
    Soporta:
      - meta["words"] con start/end
      - meta["raw_words"] con offset_raw/duration_raw (edge-tts)
    Si no hay nada, hace fallback: reparte palabras del texto por duración del audio.
    """
    if not isinstance(meta, dict) or audio_dur <= 0:
        return []

    # 1) Si viene ya normalizado
    words = meta.get("words") or []
    if words and isinstance(words, list):
        w0 = words[0] if words else {}
        if isinstance(w0, dict) and ("start" in w0 and "end" in w0 and "word" in w0):
            out = []
            for w in words:
                s = float(w.get("start", 0.0))
                e = float(w.get("end", s + 0.18))
                if e <= s:
                    e = s + 0.18
                if 0 <= s <= audio_dur:
                    out.append({"word": str(w.get("word", "")).strip(), "start": s, "end": min(e, audio_dur)})
            out = [x for x in out if x["word"]]
            if out:
                return out

    # 2) Edge-TTS RAW
    raw = meta.get("raw_words") or []
    if raw and isinstance(raw, list):
        offsets = [float(x.get("offset_raw", x.get("offset", 0))) for x in raw]
        durs = [float(x.get("duration_raw", x.get("duration", 0))) for x in raw]
        max_off = max(offsets) if offsets else 0.0

        # autodetect escala (100ns / ms / s)
        candidates = [10_000_000.0, 1000.0, 1.0]  # div
        best_div = 10_000_000.0
        best_err = float("inf")

        for div in candidates:
            last_t = max_off / div
            err = abs(last_t - audio_dur)
            if err < best_err:
                best_err = err
                best_div = div

        out = []
        for x, off, du in zip(raw, offsets, durs):
            word = (x.get("word") or x.get("text") or "").strip()
            if not word:
                continue
            start = off / best_div
            dur_s = (du / best_div) if du > 0 else 0.18
            end = start + dur_s
            if end <= start:
                end = start + 0.18
            if start <= audio_dur:
                out.append({"word": word, "start": float(start), "end": float(min(end, audio_dur))})

        out = [x for x in out if x["word"]]
        if out:
            return out

    # 3) FALLBACK: no hay WordBoundary => repartir palabras del texto
    txt = (meta.get("text") or "").strip()
    # Si tu tts.py no guarda "text", intentamos con script_text desde afuera (lo veremos en render_short)
    if not txt:
        return []

    tokens = [t for t in txt.replace("\n", " ").split(" ") if t.strip()]
    if not tokens:
        return []

    step = audio_dur / max(len(tokens), 1)
    out = []
    t = 0.0
    for tok in tokens:
        s = t
        e = min(audio_dur, t + step)
        if e <= s:
            e = min(audio_dur, s + 0.18)
        out.append({"word": tok, "start": s, "end": e})
        t += step

    return out



# ----------------- RENDER -----------------

def render_short(
    audio_path: str,
    title: str,        # ignorado
    script_text: str,  # fallback / reconcile
    out_path: str,
    topic_hint: str = "",
    meta_path: Optional[str] = None
):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    base = ImageClip(_pick_background(topic_hint)).resize((W, H))
    base = _ken_burns(base, dur)

    if not meta_path or not os.path.exists(meta_path):
        raise RuntimeError("meta_path no existe – no hay subtítulos")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    words = _normalize_word_timings(meta, audio_dur=dur)

    # --- Reconciliar: si Edge-TTS se “come” el final, lo rellenamos ---
    # tokenizamos el texto real
    tokens = [t for t in (script_text or "").replace("\n", " ").split(" ") if t.strip()]
    if tokens and words:
        # comparamos cantidad, si faltan al final, las agregamos
        if len(words) < len(tokens):
            last_end = float(words[-1]["end"])
            remaining = tokens[len(words):]
            # repartimos lo que falta en el tiempo restante (con mínimo por palabra)
            remaining_time = max(0.0, dur - last_end)
            if remaining_time > 0.05:
                step = max(0.12, remaining_time / max(1, len(remaining)))
                t = last_end
                for tok in remaining:
                    s = t
                    e = min(dur, t + step)
                    if e <= s:
                        e = min(dur, s + 0.18)
                    words.append({"word": tok, "start": s, "end": e})
                    t += step

    if not words:
        # último fallback: bloque fijo
        st = _sanitize(script_text).upper().strip()
        frame = _draw_subtitle_frame(st.split(), active_idx=-1, y_ratio=0.74)
        final = CompositeVideoClip(
            [base, _rgba_clip(frame).set_start(0).set_duration(dur)],
            size=(W, H)
        ).set_audio(audio)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
        return

    overlays = []

    WINDOW = int(os.getenv("SUB_WINDOW", "8"))
    MIN_DUR = float(os.getenv("MIN_WORD_DUR", "0.18"))
    Y_RATIO = float(os.getenv("SUB_Y", "0.74"))

    for i in range(len(words)):
        start = float(words[i]["start"])
        end_real = float(words[i].get("end", start + MIN_DUR))

        # Duración del clip = hasta la siguiente palabra (para continuidad)
        if i + 1 < len(words):
            next_start = float(words[i + 1]["start"])
            end = max(end_real, next_start)
        else:
            # ÚLTIMO: que se quede hasta el final del audio
            end = dur

        # clamp mínimo
        if end - start < MIN_DUR:
            end = start + MIN_DUR

        if start >= dur:
            break

        lo = max(0, i - WINDOW + 1)
        chunk_words = [x["word"] for x in words[lo:i + 1] if x.get("word")]
        if not chunk_words:
            continue

        frame = _draw_subtitle_frame(
            chunk_words,
            active_idx=len(chunk_words) - 1,
            y_ratio=Y_RATIO
        )

        overlays.append(
            _rgba_clip(frame)
            .set_start(start)
            .set_duration(min(end - start, dur - start))
        )

    final = CompositeVideoClip([base, *overlays], size=(W, H)).set_audio(audio)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
