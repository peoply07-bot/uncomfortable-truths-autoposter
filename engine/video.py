import os
import random
import numpy as np

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

# Resolución vertical Shorts
W, H = 1080, 1920


def sanitize_text(s: str) -> str:
    if not s:
        return s
    return (
        s.replace("\u2019", "")     # ’
         .replace("\u2018", "")     # ‘
         .replace("\u201C", "")     # “
         .replace("\u201D", "")     # ”
         .replace("\u2014", "-")    # —
         .replace("\u2013", "-")    # –
         .replace("\u2026", "...")  # …
    )


def render_short(audio_path, lines, out_path):
    # Fondo
    bg_folder = "assets/backgrounds"
    bg_file = random.choice(os.listdir(bg_folder))
    bg_path = os.path.join(bg_folder, bg_file)

    # Audio
    audio = AudioFileClip(audio_path)

    # Video base
    base = ImageClip(bg_path).resize((W, H)).set_duration(audio.duration)

    # Capa de texto (PIL -> numpy)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fuente segura en GitHub Actions
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        60
    )

    y = 400
    line_height = 80

    for line in lines:
        line = sanitize_text(line)
        draw.text((80, y), line, fill="white", font=font)
        y += line_height

    # MoviePy necesita numpy array con shape
    overlay_np = np.array(img)
    overlay = ImageClip(overlay_np).set_duration(audio.duration)

    final = CompositeVideoClip([base, overlay]).set_audio(audio)

    os.makedirs("out", exist_ok=True)
    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=2,
        preset="ultrafast"
    )
