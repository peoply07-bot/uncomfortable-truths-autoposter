import asyncio
import os
import edge_tts

async def synth(text, out):
    os.makedirs("out", exist_ok=True)
    tts = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await tts.save(out)

def make_tts(text, out):
    asyncio.run(synth(text, out))
