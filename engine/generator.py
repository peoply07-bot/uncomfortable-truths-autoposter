    import json
import os
import random
from datetime import datetime

HISTORY_PATH = "data/history.json"

SCRIPTS = [
    {
        "title": "AN UNCOMFORTABLE TRUTH",
        "script": (
            "Most people don’t fear failure.\n"
            "They fear realizing they never tried.\n"
            "Comfort feels safe—until it traps you.\n"
            "Start before you feel ready."
        ),
        "onscreen_text": [
            "MOST PEOPLE DON'T FEAR FAILURE",
            "THEY FEAR NEVER TRYING",
            "COMFORT FEELS SAFE",
            "UNTIL IT TRAPS YOU",
        ],
        "hashtags": ["#shorts", "#truth", "#mindset", "#psychology"],
    },
    {
        "title": "THE TRUTH ABOUT MOTIVATION",
        "script": (
            "Motivation is unreliable.\n"
            "Discipline is what stays.\n"
            "If you only act when you feel inspired,\n"
            "you’ll stay average forever."
        ),
        "onscreen_text": [
            "MOTIVATION IS UNRELIABLE",
            "DISCIPLINE STAYS",
            "ACT WITHOUT INSPIRATION",
            "OR STAY AVERAGE",
        ],
        "hashtags": ["#shorts", "#discipline", "#mindset", "#truth"],
    },
    {
        "title": "SUCCESS HAS A COST",
        "script": (
            "Success has a cost.\n"
            "And most people don’t want to pay it.\n"
            "They want the results,\n"
            "without the discomfort."
        ),
        "onscreen_text": [
            "SUCCESS HAS A COST",
            "MOST PEOPLE WON'T PAY IT",
            "THEY WANT RESULTS",
            "WITHOUT DISCOMFORT",
        ],
        "hashtags": ["#shorts", "#success", "#truth", "#mindset"],
    },
]


def _normalize_history(obj) -> dict:
    default = {"uploaded_titles": [], "runs": []}

    if obj is None:
        return default

    if isinstance(obj, dict):
        obj.setdefault("uploaded_titles", [])
        obj.setdefault("runs", [])
        if not isinstance(obj["uploaded_titles"], list):
            obj["uploaded_titles"] = []
        if not isinstance(obj["runs"], list):
            obj["runs"] = []
        return obj

    if isinstance(obj, list):
        titles = []
        for item in obj:
            if isinstance(item, str):
                titles.append(item)
            elif isinstance(item, dict) and "title" in item and isinstance(item["title"], str):
                titles.append(item["title"])
        return {"uploaded_titles": titles, "runs": []}

    return default


def _load_history(path: str) -> dict:
    if not os.path.exists(path):
        return {"uploaded_titles": [], "runs": []}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return _normalize_history(raw)
    except Exception:
        return {"uploaded_titles": [], "runs": []}


def _save_history(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _pick_script(history: dict) -> dict:
    used = set(t.strip().upper() for t in history.get("uploaded_titles", []) if isinstance(t, str))
    candidates = [s for s in SCRIPTS if s["title"].strip().upper() not in used]
    if not candidates:
        candidates = SCRIPTS[:]
    return random.choice(candidates)


def build_script() -> dict:
    """
    main.py espera que esto regrese un dict 'candidate' con al menos:
      - candidate["title"]
      - candidate["description"]
      - candidate["script"]         <-- CLAVE CRÍTICA (TTS)
      - candidate["onscreen_text"]  <-- para subtítulos en video
    """
    history = _load_history(HISTORY_PATH)
    picked = _pick_script(history)

    title = picked["title"].strip().upper()
    hashtags = picked.get("hashtags", ["#shorts", "#truth"])
    description = "\n".join(hashtags)

    candidate = {
        "title": title,
        "description": description,
        "script": picked["script"],                 # <-- lo que lee la voz
        "onscreen_text": picked["onscreen_text"],   # <-- lo que sale en pantalla
        "meta": {"picked_at": datetime.utcnow().isoformat() + "Z"},
    }

    history.setdefault("uploaded_titles", [])
    history.setdefault("runs", [])

    history["runs"].append({"title": title, "ts": candidate["meta"]["picked_at"]})
    _save_history(HISTORY_PATH, history)

    return candidate
