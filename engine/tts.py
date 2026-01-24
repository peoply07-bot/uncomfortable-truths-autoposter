import os
import json
import asyncio
from typing import Any, Dict, List, Optional

import edge_tts


# FORZADO a USA (no usa env var)
VOICE = "en-US-GuyNeural"   # o "en-US-JennyNeural"
RATE = "+0%"
PITCH = "+0Hz"


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
                # Guardamos RAW (sin convertir todavía)
                raw_words.append({
                    "word": (chunk.get("text") or "").strip(),
                    "offset_raw": chunk.get("offset", 0),
                    "duration_raw": chunk.get("duration", 0),
                })

    # Limpieza
    raw_words = [w for w in raw_words if w["word"]]

    meta = {
        "voice": VOICE,
        "rate": RATE,
        "pitch": PITCH,
        "raw_words": raw_words,
    }

    with open(out_meta_path, "w", encoding="utf-8") as jf:
        json.dump(meta, jf, ensure_ascii=False, indent=2)


def make_tts(text: str, out_audio_path: str, out_meta_path: Optional[str] = None) -> str:
    """
    Genera MP3 + JSON (raw).
    Devuelve la ruta del JSON.
    """
    if out_meta_path is None:
        base, _ = os.path.splitext(out_audio_path)
        out_meta_path = base + ".json"

    os.makedirs(os.path.dirname(out_audio_path) or ".", exist_ok=True)
    asyncio.run(_run_tts(text, out_audio_path, out_meta_path))
    return out_meta_path
