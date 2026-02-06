import os
import random
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image
import numpy as np

W, H = 1080, 1920


def _pick_background(topic_hint: str) -> str:
    root = "assets/backgrounds"
    if not os.path.isdir(root):
        raise RuntimeError("Missing assets/backgrounds folder")

    files = []
    for base, _, names in os.walk(root):
        for n in names:
            if n.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                files.append(os.path.join(base, n))

    if not files:
        raise RuntimeError("No background images found")

    return random.choice(files)


def _ken_burns(clip: ImageClip, duration: float) -> ImageClip:
    def zoom(t):
        return 1.0 + 0.04 * (t / max(duration, 0.001))

    def pos(t):
        return (0, int(-40 * (t / max(duration, 0.001))))

    return clip.set_duration(duration).resize(zoom).set_position(pos)


def render_short(
    audio_path: str,
    title: str,        # ignorado
    script_text: str,  # ignorado
    out_path: str,
    topic_hint: str = "",
    meta_path=None     # ignorado
):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    bg_path = _pick_background(topic_hint)
    base = ImageClip(bg_path).resize((W, H))
    base = _ken_burns(base, dur)

    final = CompositeVideoClip([base], size=(W, H)).set_audio(audio)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium"
    )
