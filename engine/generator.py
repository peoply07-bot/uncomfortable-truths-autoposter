import json
import os
import random
from datetime import date


DATA_FILE = os.path.join("data", "history.json")


def _load_history():
    if not os.path.exists(DATA_FILE):
        return {"used": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_history(hist):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)


def _pick_truth():
    # Ajusta este pool a tu estilo real
    pool = [
        "AN UNCOMFORTABLE TRUTH: MOST PEOPLE DON'T FEAR FAILURE. THEY FEAR REALIZING THEY NEVER TRIED.",
        "AN UNCOMFORTABLE TRUTH: DISCIPLINE DOESN'T CHANGE YOUR LIFE. IT REVEALS WHO YOU REALLY ARE.",
        "AN UNCOMFORTABLE TRUTH: YOU CAN'T OUTRUN YOUR OWN STANDARDS. THEY ALWAYS CATCH UP.",
        "AN UNCOMFORTABLE TRUTH: WHAT YOU CALL 'LACK OF TIME' IS OFTEN LACK OF PRIORITY.",
        "AN UNCOMFORTABLE TRUTH: CONFIDENCE IS BUILT BY KEEPING PROMISES TO YOURSELF."
    ]
    hist = _load_history()
    used = set(hist.get("used", []))

    candidates = [p for p in pool if p not in used]
    if not candidates:
        candidates = pool[:]  # recicla si ya usó todo

    chosen = random.choice(candidates)

    # guarda histórico
    if chosen not in used:
        hist["used"] = hist.get("used", []) + [chosen]
        _save_history(hist)

    return chosen


def build_candidate():
    # 1 guion único
    script = _pick_truth().strip()

    # Title estilo shorts: puede ser igual o recortado.
    # Aquí lo dejo igual para máxima consistencia.
    title = script

    # onscreen lo dividimos en líneas “grandes”
    # (Luego video.py lo animará por segmentos)
    words = script.split()
    lines = []
    line = []
    for w in words:
        line.append(w)
        if len(" ".join(line)) >= 18:
            lines.append(" ".join(line))
            line = []
    if line:
        lines.append(" ".join(line))

    # fuerza mayúsculas
    title = title.upper()
    narration = script.upper()
    onscreen_lines = [l.upper() for l in lines]

    return {
        "title": title,
        "narration": narration,
        "onscreen_lines": onscreen_lines,
        "topic_hint": script.lower()
    }
