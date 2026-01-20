import os
import random
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920

def render_short(audio_path, lines, out_path):
    bg_folder = "assets/backgrounds"
    bg = os.path.join(bg_folder, random.choice(os.listdir(bg_folder)))

    audio = AudioFileClip(audio_path)
    base = ImageClip(bg).resize((W, H)).set_duration(audio.duration)

    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    y = 400
    for line in lines:
        draw.text((200, y), line, fill="white", font=font)
        y += 60

    overlay = ImageClip(img).set_duration(audio.duration)
    final = CompositeVideoClip([base, overlay]).set_audio(audio)

    os.makedirs("out", exist_ok=True)
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
