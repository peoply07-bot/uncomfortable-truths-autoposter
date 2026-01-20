import json
import os
import random
from datetime import datetime

HISTORY_PATH = "data/history.json"

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
        "hashtags": ["#shorts", "#truth", "#mindset", "#psychology"],
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
        "hashtags": ["#shorts", "#discipline", "#mindset", "#truth"],
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
        "hashtags": ["#shorts", "#success", "#truth", "#mindset"],
    },
]


def _normalize_history(obj) -> dict:
    """
    Acepta history.json como:
    - dict: {"uploaded_titles": [...], "runs": [...]}
    - list: ["TITLE1", "TITLE2"]  -> se convierte a {"uploaded_titles":[...], "runs":[]}
    - list: [{"title":"..."}, ...] -> extrae titles si aplica
    - vacío / corrupto -> default
    """
    default = {"uploaded_titles": [], "runs": []}

    if obj is None:
        return default

    # Caso correcto: dict
    if isinstance(obj, dict):
        obj.setdefault("uploaded_titles", [])
        obj.setdefault("runs", [])
        if not isinstance(obj["uploaded_titles"], list):
            obj["uploaded_titles"] = []
        if not isinstance(obj["runs"], list):
            obj["runs"] = []
        return obj

    # Caso: list
    if isinstance(obj, list):
        titles = []
        for item in obj:
            if isinstance(item, str):
                titles.append(item)
            elif isinstance(item, dict) and "title" in item and isinstance(item["title"], str):
                titles.append(item["title"])
        return {"uploaded_titles": titles, "runs": []}

    # Caso: cualquier otra cosa
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
    main.py llama build_script() y espera:
    - title
    - description
    - narration
    - onscreen_lines
    """
    history = _load_history(HISTORY_PATH)
    script = _pick_script(history)

    title = script["title"].strip().upper()
    hashtags = script.get("hashtags", ["#shorts", "#truth"])
    description = "\n".join(hashtags)

    payload = {
        "title": title,
        "description": description,
        "narration": script["narration"],
        "onscreen_lines": script["onscreen_lines"],
        "meta": {"picked_at": datetime.utcnow().isoformat() + "Z"},
    }

    history.setdefault("runs", []).append({"title": title, "ts": payload["meta"]["picked_at"]})
    _save_history(HISTORY_PATH, history)

    return payload
