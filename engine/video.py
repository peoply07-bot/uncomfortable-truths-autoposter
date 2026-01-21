import os
import random
import json
from typing import List, Union, Tuple

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

    return clip.set_duration(duration).resize(zoom).set_position(pos)


def _normalize_text_input(text_or_lines: Union[List[str], str]) -> str:
    if text_or_lines is None:
        return ""
    if isinstance(text_or_lines, list):
        return " ".join([str(x).strip() for x in text_or_lines if str(x).strip()])
    return str(text_or_lines).strip()


def _layout_words(draw: ImageDraw.ImageDraw, words: List[str], font: ImageFont.FreeTypeFont, max_width: int) -> List[List[str]]:
    """
    Wrap en máximo 2 líneas por palabras.
    """
    lines: List[List[str]] = []
    cur: List[str] = []

    for w in words:
        if not w:
            continue

        test = (" ".join(cur + [w])).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        tw = bbox[2] - bbox[0]

        if tw <= max_width or not cur:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]

        if len(lines) == 2:
            # si ya hay 2 líneas, el resto lo pegamos en la 2da (sin seguir bajando)
            # para mantener look Shorts (no columna)
            pass

    if cur:
        if len(lines) < 2:
            lines.append(cur)
        else:
            # si ya hay 2 líneas, agrega al final de la última
            lines[-1].extend(cur)

    return lines[:2]


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return int(bbox[2] - bbox[0])


def _render_karaoke_frame(lines_words: List[List[str]],
                          font: ImageFont.FreeTypeFont,
                          highlight: Tuple[int, int],
                          reveal_upto: Tuple[int, int]) -> Image.Image:
    """
    Dibuja:
    - lo revelado en blanco (con borde negro)
    - la palabra actual en verde
    highlight: (line_idx, word_idx) para palabra actual o (-1,-1) si ninguna
    reveal_upto: (line_idx, word_idx) último revelado incluido
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    max_width = int(W * 0.86)
    line_h = int(font.size * 1.15)

    # calcular start_y para centrar bloque en zona centro-baja
    total_h = line_h * len(lines_words)
    start_y = int(H * 0.72) - int(total_h / 2)

    stroke = 6

    # precomputar ancho de cada línea para centrar
    line_texts = [" ".join(lw) for lw in lines_words]
    line_widths = [_text_width(draw, t, font) for t in line_texts]
    x_starts = [int((W - w) / 2) for w in line_widths]

    def draw_word(x, y, word, fill, shadow=False):
        if shadow:
            draw.text((x + 4, y + 4), word, font=font, fill=(0, 255, 70, 170))
        # borde negro
        for ox in range(-stroke, stroke + 1):
            for oy in range(-stroke, stroke + 1):
                if ox == 0 and oy == 0:
                    continue
                draw.text((x + ox, y + oy), word, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), word, font=font, fill=fill)

    # render
    for li, lw in enumerate(lines_words):
        y = start_y + li * line_h
        x = x_starts[li]

        # dibujar palabras hasta reveal_upto
        for wi, w in enumerate(lw):
            # decidir si esta palabra ya está revelada
            revealed = (li < reveal_upto[0]) or (li == reveal_upto[0] and wi <= reveal_upto[1])
            if not revealed:
                # no dibujar palabras futuras (esto crea el efecto "va escribiendo")
                continue

            # medir prefijo para posición
            prefix = " ".join(lw[:wi]) + (" " if wi > 0 else "")
            dx = _text_width(draw, prefix, font)
            wx = x + dx

            # highlight si corresponde
            if li == highlight[0] and wi == highlight[1]:
                draw_word(wx, y, w, fill=(0, 255, 70, 255), shadow=False)
            else:
                draw_word(wx, y, w, fill=(255, 255, 255, 255), shadow=True)

    return img


def _load_word_timings(audio_path: str) -> List[dict]:
    meta_path = audio_path + ".json"
    if not os.path.exists(meta_path):
        return []
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("words", []) if isinstance(meta, dict) else []
    except Exception:
        return []


def render_short(audio_path: str, onscreen_text: Union[List[str], str], out_path: str, topic_hint: str = ""):
    audio = AudioFileClip(audio_path)
    dur = float(audio.duration)

    # Texto del subtítulo = lo que se narra (por eso en main.py lo pasas candidate["script"])
    txt = _sanitize(_normalize_text_input(onscreen_text)).upper().strip()

    # Fondo
    bg_path = _pick_background(topic_hint)
    base = ImageClip(bg_path).resize((W, H))
    base = _ken_burns(base, dur)

    # Timings palabra por palabra del TTS
    timings = _load_word_timings(audio_path)
    if not timings:
        # fallback: subtítulo estático (no karaoke)
        # (pero si llegas aquí es porque no se generó el JSON)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        arr = np.array(img)
        final = CompositeVideoClip([base, ImageClip(arr).set_duration(dur)], size=(W, H)).set_audio(audio)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
        return

    # Tokenizar texto para layout (subtítulo normal, no letra por letra)
    words = [w for w in txt.split() if w]
    draw_tmp = ImageDraw.Draw(Image.new("RGBA", (W, H), (0, 0, 0, 0)))
    font = _font()
    lines_words = _layout_words(draw_tmp, words, font, max_width=int(W * 0.86))

    # Construir clips por “saltos” de palabra (no frame por frame)
    # Esto hace el efecto "va escribiendo" y además resalta palabra actual.
    overlays = []
    # map de palabra index global -> (line_idx, word_idx)
    mapping = []
    for li, lw in enumerate(lines_words):
        for wi, _ in enumerate(lw):
            mapping.append((li, wi))

    # Alinear timings con cantidad de palabras del texto (mejor esfuerzo)
    # edge-tts devuelve palabras del audio; si hay más/menos, usamos el mínimo
    n = min(len(mapping), len(timings))

    # Si por alguna razón hay 0, salir con fallback
    if n <= 0:
        final = CompositeVideoClip([base], size=(W, H)).set_audio(audio)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
        return

    # Generar imagen por cada palabra (cambia en cada boundary)
    for i in range(n):
        start = float(timings[i]["offset_s"])
        end = float(timings[i]["offset_s"] + timings[i]["duration_s"])
        # si duration viene muy corta, ampliamos un poco
        end = max(end, start + 0.08)

        # Última palabra: extiende hasta el final del audio
        if i == n - 1:
            end = dur

        highlight = mapping[i]
        reveal_upto = mapping[i]

        frame = _render_karaoke_frame(lines_words, font, highlight=highlight, reveal_upto=reveal_upto)
        ov = ImageClip(np.array(frame)).set_start(start).set_duration(max(0.01, end - start))
        overlays.append(ov)

    final = CompositeVideoClip([base, *overlays], size=(W, H)).set_audio(audio)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
