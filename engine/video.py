import os
import random
import math
import numpy as np

from PIL import Image, ImageDraw, ImageFont

# --- Compatibility patch for Pillow>=10 (moviepy 1.0.3 expects Image.ANTIALIAS) ---
if not hasattr(Image, "ANTIALIAS"):
    # Pillow>=10 uses Image.Resampling
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
import moviepy.video.fx.all as vfx


W, H = 1080, 1920
BG_DIR = os.path.join("assets", "backgrounds")

# Subtitles layout
SUB_Y = 1200                   # vertical position (pixels from top)
FONT_SIZE = 92
LINE_SPACING = 18
STROKE_W = 6


def _pick_font():
    """
    Prefer a real TTF font so Unicode (quotes, etc.) doesn't crash.
    GitHub ubuntu runners usually have DejaVu fonts installed.
    """
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, FONT_SIZE)
    # Fallback (less capable for unicode)
    return ImageFont.load_default()


FONT = _pick_font()


def sanitize_text(s: str) -> str:
    """
    Normalize risky punctuation that tends to break rendering on some fonts.
    """
    if not s:
        return s
    return (
        s.replace("\u2019", "'")   # ’
         .replace("\u2018", "'")   # ‘
         .replace("\u201C", '"')   # “
         .replace("\u201D", '"')   # ”
         .replace("\u2014", "-")   # —
         .replace("\u2013", "-")   # –
         .replace("\u2026", "...") # …
    )


def _list_backgrounds() -> list[str]:
    if not os.path.isdir(BG_DIR):
        raise FileNotFoundError(f"Missing backgrounds folder: {BG_DIR}")

    files = [
        os.path.join(BG_DIR, f)
        for f in os.listdir(BG_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]
    if not files:
        raise FileNotFoundError(f"No background images found in: {BG_DIR}")
    return files


def _fit_to_vertical(path: str) -> ImageClip:
    """
    Load image, scale and center-crop to exact 9:16 (1080x1920).
    """
    clip = ImageClip(path)

    # Ensure it fully covers the frame, then crop center
    scale = max(W / clip.w, H / clip.h)
    clip = clip.resize(scale)

    x1 = (clip.w - W) / 2
    y1 = (clip.h - H) / 2
    clip = clip.crop(x1=x1, y1=y1, x2=x1 + W, y2=y1 + H)
    return clip


def _ken_burns(clip: ImageClip, duration: float, zoom_max: float = 1.08) -> ImageClip:
    """
    Subtle zoom-in over time (Ken Burns).
    """
    def zoom(t):
        if duration <= 0:
            return 1.0
        return 1.0 + (zoom_max - 1.0) * (t / duration)

    return clip.fx(vfx.resize, zoom)


def _draw_text_with_stroke(draw: ImageDraw.ImageDraw, pos, text, fill, stroke_fill="black", stroke_w=STROKE_W):
    x, y = pos
    # stroke (manual)
    for ox in range(-stroke_w, stroke_w + 1):
        for oy in range(-stroke_w, stroke_w + 1):
            if ox == 0 and oy == 0:
                continue
            if ox * ox + oy * oy <= stroke_w * stroke_w:
                draw.text((x + ox, y + oy), text, font=FONT, fill=stroke_fill)
    # main text
    draw.text((x, y), text, font=FONT, fill=fill)


def _text_size(draw: ImageDraw.ImageDraw, text: str):
    bbox = draw.textbbox((0, 0), text, font=FONT)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _render_subtitle_image(line: str) -> np.ndarray:
    """
    Render one subtitle line as transparent RGBA image (numpy array).
    Supports highlight using pipe delimiter:
      "DURING|DECADES" -> DURING (green) + DECADES (white)
    If no pipe, highlights the first word in green.
    """
    line = sanitize_text(line).strip()
    if not line:
        # empty transparent
        img = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
        return np.array(img)

    # Highlight logic
    green_part = None
    rest_part = None

    if "|" in line:
        parts = line.split("|", 1)
        green_part = parts[0].strip()
        rest_part = parts[1].strip()
    else:
        words = line.split()
        if len(words) >= 2:
            green_part = words[0].strip()
            rest_part = " ".join(words[1:]).strip()
        else:
            green_part = line
            rest_part = ""

    # Create canvas
    img = Image.new("RGBA", (W, 320), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Measure and center combined line
    gp = green_part
    rp = rest_part

    gp_w, gp_h = _text_size(draw, gp) if gp else (0, 0)
    rp_w, rp_h = _text_size(draw, rp) if rp else (0, 0)
    space_w, _ = _text_size(draw, " ")

    total_w = gp_w + (space_w if gp and rp else 0) + rp_w
    x = int((W - total_w) / 2)
    y = 20  # inside the subtitle band

    # Draw green part
    if gp:
        _draw_text_with_stroke(draw, (x, y), gp, fill="#25D366")  # green
        x += gp_w

    # Space then rest
    if gp and rp:
        x += space_w
    if rp:
        _draw_text_with_stroke(draw, (x, y), rp, fill="white")

    return np.array(img)


def _build_background_track(total_duration: float) -> ImageClip:
    """
    Creates a background video track by stitching multiple images with movement.
    """
    bg_files = _list_backgrounds()

    # We want multiple images; ~4-6 seconds each
    seg_min = 4.0
    seg_max = 5.5

    clips = []
    t = 0.0
    while t < total_duration - 0.05:
        seg = min(random.uniform(seg_min, seg_max), total_duration - t)
        path = random.choice(bg_files)
        base = _fit_to_vertical(path).set_duration(seg)
        base = _ken_burns(base, duration=seg, zoom_max=random.uniform(1.06, 1.10))
        clips.append(base)
        t += seg

    if not clips:
        # fallback single background
        path = random.choice(bg_files)
        base = _fit_to_vertical(path).set_duration(total_duration)
        base = _ken_burns(base, duration=total_duration, zoom_max=1.08)
        return base

    return concatenate_videoclips(clips, method="compose")


def render_short(audio_path: str, lines: list[str], out_path: str):
    """
    Main entry called by main.py
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    audio = AudioFileClip(audio_path)
    total_dur = float(audio.duration)

    # Background (multiple images + motion)
    bg = _build_background_track(total_dur)

    # Subtitles timing
    lines = [sanitize_text(x) for x in (lines or []) if str(x).strip()]
    if not lines:
        lines = ["AN UNCOMFORTABLE TRUTH"]

    per_line = max(1.8, total_dur / len(lines))  # prevents too-fast flashes
    # If the audio is short, compress a bit but keep readable
    per_line = min(per_line, 3.2)

    subtitle_clips = []
    cur = 0.0
    for i, line in enumerate(lines):
        if cur >= total_dur - 0.05:
            break

        dur = min(per_line, total_dur - cur)
        img_arr = _render_subtitle_image(line)

        sub = (
            ImageClip(img_arr, ismask=False)
            .set_start(cur)
            .set_duration(dur)
            .set_pos(("center", SUB_Y))
            .fx(vfx.fadein, 0.12)
            .fx(vfx.fadeout, 0.12)
        )
        subtitle_clips.append(sub)
        cur += dur

    final = CompositeVideoClip([bg] + subtitle_clips, size=(W, H)).set_audio(audio)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="veryfast",
        threads=4,
        ffmpeg_params=["-movflags", "+faststart"],
        verbose=False,
        logger=None,
    )
