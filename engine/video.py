import os
import json
import random
from typing import List, Dict, Any, Tuple, Optional

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
    return lines[:2]  # máximo 2 líneas


def _draw_subtitle_frame(words: List[str], active_idx: int, y_ratio: float = 0.72) -> Image.Image:
    """
    Dibuja un subtítulo (1-2 líneas) en blanco con borde negro,
    y resalta la palabra activa en verde.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = _font(74)
    stroke = 6
    max_width = int(W * 0.88)

    # preparar texto saneado
    clean = [_sanitize(w).upper() for w in words if w.strip()]
    if not clean:
        return img

    lines = _wrap_words(draw, clean, font, max_width=max_width)

    # calcular altura total
    line_h = 95
    total_h = len(lines) * line_h
    y0 = int(H * y_ratio) - total_h // 2

    # índice global
    idx_global = 0

    for li, line_words in enumerate(lines):
        line_text = " ".join(line_words)
        bbox = draw.textbbox((0, 0), line_text, font=font)
        tw = bbox[2] - bbox[0]
        x = int((W - tw) / 2)
        y = y0 + li * line_h

        # Primero dibuja línea completa (borde + blanco)
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox == 0 and oy == 0:
                    continue
                draw.text((x + ox, y + oy), line_text, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line_text, font=font, fill=(255, 255, 255, 255))

        # Luego pinta SOLO la palabra activa en verde encima
        # calculamos offset x por palabra
        cx = x
        for wi, w in enumerate(line_words):
            w_text = w
            prefix = "" if wi == 0 else " "
            prefix_bbox = draw.textbbox((0, 0), prefix, font=font)
            pxw = prefix_bbox[2] - prefix_bbox[0]
            cx += pxw

            w_bbox = draw.textbbox((0, 0), w_text, font=font)
            ww = w_bbox[2] - w_bbox[0]

            if idx_global == active_idx:
                # Verde con borde negro
                for ox in range(-stroke, stroke + 1):
                    for oy in range(-stroke, stroke + 1):
                        if ox == 0 and oy == 0:
                            continue
                        draw.text((cx + ox, y + oy), w_text, font=font, fill=(0, 0, 0, 255))
                draw.text((cx, y), w_text, font=font, fill=(0, 255, 0, 255))

            cx += ww
            idx_global += 1

    return img


def _draw_title(title: str) -> Image.Image:
    """
    Título grande, horizontal, estilo thumbnail (borde negro).
    """
    title = _sanitize(title).strip().upper()
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(92)
    stroke = 8

    # centrado algo más arriba que subtítulo
    y = int(H * 0.20)

    bbox = draw.textbbox((0, 0), title, font=font)
    tw = bbox[2] - bbox[0]
    x = int((W - tw) / 2)

    for ox in range(-stroke, stroke + 1):
        for oy in range(-stroke, stroke + 1):
            if ox == 0 and oy == 0:
                continue
            draw.text((x + ox, y + oy), title, font=font, fill=(0, 0, 0, 255))
    draw.text((x, y), title, font=font, fill=(255, 255, 255, 255))
    return img


def render_short(
    audio_path: str,
    title: str,
    script_text: str,
    out_path: str,
    topic_hint: str = "",
    meta_path: Optional[str] = None
):
    """
    - title: se muestra al inicio (horizontal)
    - script_text: se usa para subtítulos
    - meta_path: JSON con timings palabra a palabra (de engine/tts.py)
    """
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    bg_path = _pick_background(topic_hint or title)
    base = ImageClip(bg_path).resize((W, H))
    base = _ken_burns(base, dur)

    overlays: List[ImageClip] = []

    # 1) TÍTULO al inicio (1.4s)
    if title and title.strip():
        timg = _draw_title(title)
        tclip = _rgba_clip(timg).set_start(0).set_duration(min(1.4, dur))
        overlays.append(tclip)

    # 2) Subtítulos sincronizados por palabra
    words = []
    if meta_path and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        words = meta.get("words", [])

    # fallback: si no hay meta, no hay sincronía real
    if not words:
        # muestra texto completo como 1 bloque (no recomendado, pero evita “sin nada”)
        st = _sanitize(script_text).upper().strip()
        if st:
            simple = _draw_subtitle_frame(st.split(), active_idx=-1, y_ratio=0.72)
            overlays.append(_rgba_clip(simple).set_start(1.4).set_duration(max(0.1, dur - 1.4)))
    else:
        # Construimos una ventana de palabras (para no mostrar 200 palabras a la vez)
        # Mostramos las últimas ~10 palabras y resaltamos la actual.
        window = 10

        # Genera clips por palabra (suave y sincronizado)
        for i, w in enumerate(words):
            start = float(w.get("start", 0.0))
            end = float(w.get("end", start + 0.18))

            # Evita que el subtítulo arranque debajo del título
            start = max(start, 1.2)

            if end <= start or start >= dur:
                continue

            lo = max(0, i - (window - 1))
            chunk_words = [x["word"] for x in words[lo:i + 1]]
            active = len(chunk_words) - 1  # el último es el activo

            frame = _draw_subtitle_frame(chunk_words, active_idx=active, y_ratio=0.74)
            overlays.append(_rgba_clip(frame).set_start(start).set_duration(min(end - start, dur - start)))

    final = CompositeVideoClip([base, *overlays], size=(W, H)).set_audio(audio)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
