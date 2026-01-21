import os
import random
from typing import List, Union

import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920


def _font():
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


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]

    lines = []
    cur = words[0]
    for w in words[1:]:
        test = cur + " " + w
        bbox = draw.textbbox((0, 0), test, font=font)
        tw = bbox[2] - bbox[0]
        if tw <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


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
        if any(k in hint for k in kws):
            if os.path.isdir(os.path.join(root, folder)):
                chosen_folder = os.path.join(root, folder)
                break

    if chosen_folder is None:
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
    def zoom(t):
        return 1.00 + 0.03 * (t / max(duration, 0.001))

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
    Texto normal (no letra por letra), máximo 2 líneas, centrado, con:
    - borde negro
    - sombra verde suave
    - texto blanco encima
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font()

    text = " ".join([_sanitize(str(l)).strip() for l in lines if l and str(l).strip()]).upper().strip()
    if not text:
        return img

    max_width = int(W * 0.86)
    wrapped = _wrap_text(draw, text, font, max_width=max_width)[:2]

    line_h = int(font.size * 1.15)
    total_h = line_h * len(wrapped)
    start_y = int(H * 0.72) - int(total_h / 2)

    stroke = 6
    # sombra verde (offset leve)
    shadow_dx, shadow_dy = 4, 4
    shadow_color = (0, 255, 70, 170)  # verde con alpha

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = int((W - tw) / 2)
        y = start_y + i * line_h

        # borde negro
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox == 0 and oy == 0:
                    continue
                draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0, 255))

        # sombra verde (una sola pasada, suave)
        draw.text((x + shadow_dx, y + shadow_dy), line, font=font, fill=shadow_color)

        # texto blanco
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    return img


def _normalize_onscreen(onscreen_lines: Union[List[str], str]) -> List[str]:
    """
    FIX CRÍTICO:
    Si onscreen_lines es string, NO iterar carácter por carácter.
    Lo convertimos a lista.
    """
    if onscreen_lines is None:
        return []

    if isinstance(onscreen_lines, str):
        s = onscreen_lines.strip()
        if not s:
            return []
        # Si trae saltos, respétalos como “frases”
        parts = [p.strip() for p in s.split("\n") if p.strip()]
        return parts if parts else [s]

    # si ya es lista
    return [str(x).strip() for x in onscreen_lines if str(x).strip()]


def _split_into_segments(onscreen_lines: List[str], max_lines_per_screen: int = 1) -> List[List[str]]:
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


def render_short(audio_path: str, onscreen_lines: Union[List[str], str], out_path: str, topic_hint: str = ""):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    # FIX: evitar letra-por-letra
    onscreen_lines = _normalize_onscreen(onscreen_lines)

    bg_path = _pick_background(topic_hint)
    base = ImageClip(bg_path).resize((W, H))
    base = _ken_burns(base, dur)

    # Si solo tienes 1 frase, se mantiene todo el video (subtítulo normal)
    if len(onscreen_lines) <= 1:
        segments = [onscreen_lines if onscreen_lines else [""]]
        seg_durs = [dur]
    else:
        # 1 frase por “pantalla”
        segments = _split_into_segments(onscreen_lines, max_lines_per_screen=1)
        weights = [max(1, sum(len(str(x)) for x in seg)) for seg in segments]
        total_w = sum(weights) if sum(weights) > 0 else 1
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
