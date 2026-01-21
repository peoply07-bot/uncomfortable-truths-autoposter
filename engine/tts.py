import os
import json
import asyncio
from typing import Optional, Dict, Any, List

import edge_tts


# Voz masculina seria (puedes cambiarla aquí)
VOICE = os.getenv("TTS_VOICE", "es-ES-AlvaroNeural")
RATE = os.getenv("TTS_RATE", "+0%")   # ejemplo: "+5%"
PITCH = os.getenv("TTS_PITCH", "+0Hz")


async def _run_tts(text: str, out_audio_path: str, out_meta_path: str):
    os.makedirs(os.path.dirname(out_audio_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(out_meta_path) or ".", exist_ok=True)

    communicate = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH)

    words: List[Dict[str, Any]] = []

    # edge-tts entrega audio + eventos WordBoundary con offsets reales
    with open(out_audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offsets suelen venir en 100-ns (10,000,000 = 1s)
                off = chunk.get("offset", 0) / 10_000_000
                dur = chunk.get("duration", 0) / 10_000_000
                w = chunk.get("text", "").strip()
                if w:
                    words.append({
                        "word": w,
                        "start": float(off),
                        "end": float(off + dur if dur > 0 else off + 0.18)  # fallback si dur=0
                    })

    meta = {"voice": VOICE, "rate": RATE, "pitch": PITCH, "words": words}

    with open(out_meta_path, "w", encoding="utf-8") as jf:
        json.dump(meta, jf, ensure_ascii=False, indent=2)


def make_tts(text: str, out_audio_path: str, out_meta_path: Optional[str] = None) -> str:
    """
    Genera audio MP3 y un meta JSON con timestamps de palabras.
    Devuelve la ruta del meta JSON.
    """
    if out_meta_path is None:
        base, _ = os.path.splitext(out_audio_path)
        out_meta_path = base + ".json"

    # IMPORTANTÍSIMO: crear carpeta out antes
    os.makedirs(os.path.dirname(out_audio_path) or ".", exist_ok=True)

    asyncio.run(_run_tts(text, out_audio_path, out_meta_path))
    return out_meta_path
