import os
import random
from typing import List, Tuple

import numpy as np
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, vfx
)
from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1920


def _font():
    # En GitHub runner normalmente existe DejaVuSans
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, 86)
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
    """
    Selección por tema usando tus imágenes locales.
    Estructura recomendada:
      assets/backgrounds/space/*.jpg
      assets/backgrounds/mindset/*.jpg
      assets/backgrounds/money/*.jpg
      assets/backgrounds/general/*.jpg   (fallback)
    Si no existen subcarpetas, usa assets/backgrounds raíz.
    """
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
        if any(k in hint for k in kws):
            if os.path.isdir(os.path.join(root, folder)):
                chosen_folder = os.path.join(root, folder)
                break

    if chosen_folder is None:
        # usa general si existe
        if os.path.isdir(os.path.join(root, "general")):
            chosen_folder = os.path.join(root, "general")
        else:
            chosen_folder = root

    files = []
    for fn in os.listdir(chosen_folder):
        if fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            files.append(os.path.join(chosen_folder, fn))

    if not files:
        raise RuntimeError(f"No images found in {chosen_folder}")

    return random.choice(files)


def _ken_burns(clip: ImageClip, duration: float) -> ImageClip:
    """
    Zoom + pan suave (Ken Burns).
    """
    # Zoom leve (3% total)
    def zoom(t):
        return 1.00 + 0.03 * (t / max(duration, 0.001))

    # Pan leve
    # MoviePy permite position como función (x,y)
    max_dx = 40
    max_dy = 60

    def pos(t):
        p = t / max(duration, 0.001)
        dx = int((p - 0.5) * 2 * max_dx)
        dy = int((0.5 - p) * 2 * max_dy)
        return (dx, dy)

    return (
        clip
        .set_duration(duration)
        .resize(zoom)
        .set_position(pos)
    )


def _draw_text_image(lines: List[str]) -> Image.Image:
    """
    Renderiza texto grande con borde negro estilo shorts.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font()

    # Posición estilo “centro-bajo”
    y = int(H * 0.62)

    for line in lines:
        line = _sanitize(line).upper()
        if not line:
            continue

        # Calcula ancho aproximado
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = int((W - tw) / 2)

        # Borde (stroke manual)
        stroke = 6
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox == 0 and oy == 0:
                    continue
                draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0, 255))

        # Texto blanco principal
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

        y += 110  # separación vertical

    return img


def _split_into_segments(onscreen_lines: List[str], max_lines_per_screen: int = 2) -> List[List[str]]:
    """
    Divide líneas en pantallas de 1-2 líneas grandes.
    """
    segs = []
    cur = []
    for l in onscreen_lines:
        cur.append(l)
        if len(cur) >= max_lines_per_screen:
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    return segs


def render_short(audio_path: str, onscreen_lines: List[str], out_path: str, topic_hint: str = ""):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    bg_path = _pick_background(topic_hint)
    base = ImageClip(bg_path).resize((W, H))
    base = _ken_burns(base, dur)

    # Segmentos sincronizados (simple y efectivo):
    segments = _split_into_segments(onscreen_lines, max_lines_per_screen=2)

    # Duración proporcional a cantidad de texto por segmento
    weights = [max(1, sum(len(x) for x in seg)) for seg in segments]
    total_w = sum(weights)
    seg_durs = [dur * (w / total_w) for w in weights]

    overlays = []
    t = 0.0
    for seg, sd in zip(segments, seg_durs):
        img = _draw_text_image(seg)
        arr = np.array(img)
        ov = ImageClip(arr).set_start(t).set_duration(sd)
        overlays.append(ov)
        t += sd

    final = CompositeVideoClip([base, *overlays], size=(W, H)).set_audio(audio)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
