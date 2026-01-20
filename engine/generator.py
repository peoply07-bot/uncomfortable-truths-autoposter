import json
import os
import random
from datetime import datetime

HISTORY_PATH = "data/history.json"

# Banco simple de guiones. Luego lo hacemos “inteligente”.
SCRIPTS = [
    {
        "title": "AN UNCOMFORTABLE TRUTH",
        "narration": (
            "Most people don’t fear failure.\n"
            "They fear realizing they never tried.\n"
            "Comfort feels safe—until it traps you.\n"
            "Start before you feel ready."
        ),
        "onscreen_lines": [
            "MOST PEOPLE DON'T FEAR FAILURE",
            "THEY FEAR NEVER TRYING",
            "COMFORT FEELS SAFE",
            "UNTIL IT TRAPS YOU",
        ],
        "hashtags": ["#shorts", "#truth", "#mindset", "#psychology"]
    },
    {
        "title": "THE TRUTH ABOUT MOTIVATION",
        "narration": (
            "Motivation is unreliable.\n"
            "Discipline is what stays.\n"
            "If you only act when you feel inspired,\n"
            "you’ll stay average forever."
        ),
        "onscreen_lines": [
            "MOTIVATION IS UNRELIABLE",
            "DISCIPLINE STAYS",
            "ACT WITHOUT INSPIRATION",
            "OR STAY AVERAGE",
        ],
        "hashtags": ["#shorts", "#discipline", "#mindset", "#truth"]
    },
    {
        "title": "SUCCESS HAS A COST",
        "narration": (
            "Success has a cost.\n"
            "And most people don’t want to pay it.\n"
            "They want the results,\n"
            "without the discomfort."
        ),
        "onscreen_lines": [
            "SUCCESS HAS A COST",
            "MOST PEOPLE WON'T PAY IT",
            "THEY WANT RESULTS",
            "WITHOUT DISCOMFORT",
        ],
        "hashtags": ["#shorts", "#success", "#truth", "#mindset"]
    },
]

def _load_history(path: str) -> dict:
    if not os.path.exists(path):
        return {"uploaded_titles": [], "runs": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"uploaded_titles": [], "runs": []}

def _save_history(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _pick_script(history: dict) -> dict:
    used = set([t.strip().upper() for t in history.get("uploaded_titles", [])])

    candidates = [s for s in SCRIPTS if s["title"].strip().upper() not in used]
    if not candidates:
        # Si ya usó todos, vuelve a permitir repetición (pero registra el run igual).
        candidates = SCRIPTS[:]

    return random.choice(candidates)

def build_script() -> dict:
    """
    main.py espera que exista build_script() en engine.generator
    y que devuelva un dict con title, description, narration y onscreen_lines.
    """
    history = _load_history(HISTORY_PATH)
    script = _pick_script(history)

    # Reglas de estilo que pediste:
    # - Título en MAYÚSCULA
    # - El título debe estar alineado con el texto/voz (aquí lo garantizamos porque sale del mismo objeto)
    title = script["title"].strip().upper()

    # Descripción (hashtags)
    hashtags = script.get("hashtags", ["#shorts", "#truth"])
    description = "\n".join(hashtags)

    payload = {
        "title": title,
        "description": description,
        "narration": script["narration"],
        "onscreen_lines": script["onscreen_lines"],
        # opcional: para debug
        "meta": {
            "picked_at": datetime.utcnow().isoformat() + "Z",
        }
    }

    # Guardar registro (NO lo marcamos como “uploaded” todavía; eso lo debe hacer youtube.py cuando sube OK)
    history.setdefault("runs", []).append({"title": title, "ts": payload["meta"]["picked_at"]})
    _save_history(HISTORY_PATH, history)

    return payload
