import time
from engine.generator import build_script
from engine.uniqueness import load_history, save_history, accept_candidate
from engine.tts import make_tts
from engine.video import render_short
from engine.youtube import upload_short

def description_from_tags(tags):
    return "#shorts\n" + " ".join(f"#{t}" for t in tags)

def run():
    history = load_history()

    candidate = None
    for _ in range(30):
        c = build_script()
        if accept_candidate(c, history):
            candidate = c
            break

    if not candidate:
        raise RuntimeError("No se pudo generar contenido único")

    ts = str(int(time.time()))
    audio = f"out/{ts}.mp3"
    video = f"out/{ts}.mp4"

    make_tts(candidate["script"], audio)
    render_short(audio, candidate["onscreen_text"], video)

    upload_short(
        video,
        f'{candidate["title"]} #shorts',
        description_from_tags(candidate["hashtags"])
    )

    history.append({
        "title": candidate["title"],
        "script": candidate["script"]
    })
    save_history(history)

if __name__ == "__main__":
    run()
