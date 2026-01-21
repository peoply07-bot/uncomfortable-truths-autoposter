import asyncio
import json
import os
import edge_tts

VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")


async def _run(text: str, out_audio_path: str, out_meta_path: str):
    communicate = edge_tts.Communicate(text=text, voice=VOICE)

    words = []
    with open(out_audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration vienen en ticks de 100ns
                offset_s = chunk["offset"] / 10_000_000
                duration_s = chunk["duration"] / 10_000_000
                w = (chunk.get("text") or "").strip()
                if w:
                    words.append({
                        "text": w,
                        "offset_s": float(offset_s),
                        "duration_s": float(duration_s),
                    })

    meta = {
        "voice": VOICE,
        "words": words,
    }
    with open(out_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def make_tts(text: str, out_audio_path: str):
    """
    Genera audio y un JSON con tiempos por palabra:
      out_audio_path + ".json"
    """
    out_meta_path = out_audio_path + ".json"
    asyncio.run(_run(text, out_audio_path, out_meta_path))
