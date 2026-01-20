import os
import asyncio
import edge_tts


VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")  # Hombre serio USA
RATE = os.getenv("TTS_RATE", "-5%")               # Ligeramente más lento (mejor claridad)
PITCH = os.getenv("TTS_PITCH", "-2Hz")            # Un poco más grave


async def tts_to_file(text: str, out_path: str):
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


def synthesize(text: str, out_path: str):
    """
    Sync wrapper used by the rest of the code.
    """
    asyncio.run(tts_to_file(text, out_path))
