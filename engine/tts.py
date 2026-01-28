import os
import json
import asyncio
from typing import Any, Dict, List, Optional

import edge_tts

# FORZADO a USA
VOICE = "en-US-GuyNeural"   # o "en-US-JennyNeural"
RATE = "+0%"
PITCH = "+0Hz"

TICKS_PER_SECOND = 10_000_000  # 100ns units


async def _run_tts(text: str, out_audio_path: str, out_meta_path: str):
    os.makedirs(os.path.dirname(out_audio_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(out_meta_path) or ".", exist_ok=True)

    communicate = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH)

    raw_words: List[Dict[str, Any]] = []

    with open(out_audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                w = (chunk.get("text") or "").strip()
                if not w:
                    continue

                offset_raw = int(chunk.get("offset", 0) or 0)
                duration_raw = int(chunk.get("duration", 0) or 0)

                raw_words.append({
                    "word": w,
                    "offset_raw": offset_raw,
                    "duration_raw": duration_raw,
                })

    # Construimos words en segundos (lo que espera video.py)
    words: List[Dict[str, Any]] = []
    for w in raw_words:
        start = float(w["offset_raw"]) / TICKS_PER_SECOND
        end = float(w["offset_raw"] + w["duration_raw"]) / TICKS_PER_SECOND

        # Guardas por seguridad
        if end <= start:
            end = start + 0.06  # mínimo visible

        words.append({
            "word": w["word"],
            "start": round(start, 3),
            "end": round(end, 3),
        })

    meta = {
        "voice": VOICE,
        "rate": RATE,
        "pitch": PITCH,
        "text": text,
        "words": words,        # <-- CLAVE (video.py usa esto)
        "raw_words": raw_words # opcional, por si quieres debug
    }

    with open(out_meta_path, "w", encoding="utf-8") as jf:
        json.dump(meta, jf, ensure_ascii=False, indent=2)


def make_tts(text: str, out_audio_path: str, out_meta_path: Optional[str] = None) -> str:
    """
    Genera MP3 + JSON con timings palabra a palabra.
    Devuelve la ruta del JSON.
    """
    if out_meta_path is None:
        base, _ = os.path.splitext(out_audio_path)
        out_meta_path = base + ".json"

    os.makedirs(os.path.dirname(out_audio_path) or ".", exist_ok=True)
    asyncio.run(_run_tts(text, out_audio_path, out_meta_path))
    return out_meta_path
