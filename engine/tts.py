import os
import asyncio
import edge_tts


VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")  # Hombre serio USA
RATE = os.getenv("TTS_RATE", "-5%")               # un poco más lento
PITCH = os.getenv("TTS_PITCH", "-2Hz")            # un poco más grave


async def _tts_to_file(text: str, out_path: str):
    text = (text or "").strip()
    if not text:
        raise ValueError("TTS text is empty")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(out_path)


def make_tts(text: str, out_path: str):
    """
    Mantengo este nombre porque main.py lo importa así:
      from engine.tts import make_tts
    """
    asyncio.run(_tts_to_file(text, out_path))


# Alias extra por si en algún archivo aparece otro nombre
def synthesize(text: str, out_path: str):
    return make_tts(text, out_path)
