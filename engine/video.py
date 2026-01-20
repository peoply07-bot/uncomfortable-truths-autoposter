import os
import random

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

# Resolución vertical Shorts
W, H = 1080, 1920


def sanitize_text(s: str) -> str:
    if not s:
        return s
    return (
        s.replace("\u2019", "")   # ’
         .replace("\u2018", "")   # ‘
         .replace("\u201C", "")   # “
         .replace("\u201D", "")   # ”
         .replace("\u2014", "-")  # —
         .replace("\u2013", "-")  # –
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

    # Capa de texto
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fuente segura (Unicode OK)
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        60
    )

    # Posición inicial
    y = 400
    line_height = 80

    for line in lines:
        line = sanitize_text(line)
        draw.text((80, y), line, fill="white", font=font)
        y += line_height

    overlay = ImageClip(img).set_duration(audio.duration)

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
