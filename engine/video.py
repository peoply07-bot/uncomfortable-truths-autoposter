import os
import random
from typing import List

import numpy as np
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip
)
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
        if any(k in hint for k in kws):
            if os.path.isdir(os.path.join(root, folder)):
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

    return (
        clip.set_duration(duration)
            .resize(zoom)
            .set_position(pos)
    )


def _draw_text_image(lines: List[str]) -> Image.Image:
    """
    Texto grande con borde negro, centrado y en zona baja (visible en Shorts).
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = _font(86)

    # Más abajo pero siempre visible (ajustado)
    y = int(H * 0.68)

    for line in lines:
        line = _sanitize(line).strip().upper()
        if not line:
            continue

        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = int((W - tw) / 2)

        stroke = 6
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox == 0 and oy == 0:
                    continue
                draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0, 255))

        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += 110

    return img


def _split_into_segments(onscreen_lines: List[str], max_lines_per_screen: int = 2) -> List[List[str]]:
    segs = []
    cur = []
    for l in onscreen_lines:
        l = (l or "").strip()
        if not l:
            continue
        cur.append(l)
        if len(cur) >= max_lines_per_screen:
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    return segs


def _imageclip_rgba_with_mask(pil_rgba: Image.Image) -> ImageClip:
    """
    CRÍTICO: MoviePy puede ignorar alfa.
    Solución: crear clip RGB + mask explícita (alpha/255).
    """
    arr = np.array(pil_rgba)  # (H,W,4)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3] / 255.0

    clip = ImageClip(rgb)
    mask = ImageClip(alpha, ismask=True)
    clip = clip.set_mask(mask)
    return clip


def render_short(audio_path: str, onscreen_lines: List[str], out_path: str, topic_hint: str = ""):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    bg_path = _pick_background(topic_hint)
    base = ImageClip(bg_path).resize((W, H))
    base = _ken_burns(base, dur)

    segments = _split_into_segments(onscreen_lines, max_lines_per_screen=2)

    if not segments:
        # si no hay texto, igual saca video con fondo + audio
        final = CompositeVideoClip([base], size=(W, H)).set_audio(audio)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
        return

    # Duración proporcional al texto
    weights = [max(1, sum(len(x) for x in seg)) for seg in segments]
    total_w = sum(weights)
    seg_durs = [dur * (w / total_w) for w in weights]

    overlays = []
    t = 0.0
    for seg, sd in zip(segments, seg_durs):
        img = _draw_text_image(seg)
        ov = _imageclip_rgba_with_mask(img).set_start(t).set_duration(sd)
        overlays.append(ov)
        t += sd

    final = CompositeVideoClip([base, *overlays], size=(W, H)).set_audio(audio)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
