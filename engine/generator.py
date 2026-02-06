import json
import os
import random

SCRIPTS_PATH = os.path.join("data", "scripts.json")

FALLBACK = [
    {
        "title": "AN UNCOMFORTABLE TRUTH",
        "script": (
            "Most people don't fear failure. "
            "They fear realizing they're replaceable. "
            "Comfort feels safe—until it traps you."
        ),
        "onscreen_text": "MOST PEOPLE DON'T FEAR FAILURE.\nTHEY FEAR BEING REPLACEABLE.",
        "hashtags": ["psychology", "mindset", "truth"]
    }
]

_STATE_PATH = os.path.join("data", ".last_pick.json")


def _load_scripts():
    if not os.path.exists(SCRIPTS_PATH):
        return FALLBACK

    with open(SCRIPTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = data.get("items") or data.get("scripts") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []

    return items if items else FALLBACK


def _load_last_index():
    if not os.path.exists(_STATE_PATH):
        return None
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("last_index")
    except Exception:
        return None


def _save_last_index(idx):
    os.makedirs("data", exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"last_index": idx}, f)


def _normalize_candidate(raw):
    c = dict(raw) if isinstance(raw, dict) else {}

    title = c.get("title") or "AN UNCOMFORTABLE TRUTH"
    title = str(title).strip().upper()

    script = (
        c.get("script")
        or c.get("narration")
        or c.get("voiceover")
        or ""
    ).strip()
    if not script:
        script = FALLBACK[0]["script"]

    onscreen = c.get("onscreen_text")
    if not onscreen:
        s = script.replace("\n", " ")
        onscreen = s[:80].upper()
        if len(onscreen) > 40:
            onscreen = onscreen[:40] + "\n" + onscreen[40:80]
    else:
        onscreen = str(onscreen).strip().upper()

    tags = c.get("hashtags") or []
    if isinstance(tags, str):
        tags = tags.replace(",", " ").split()
    tags = [t.strip("# ").lower() for t in tags if t.strip()]
    if not tags:
        tags = ["psychology", "mindset", "truth"]

    return {
        "title": title,
        "script": script,
        "onscreen_text": onscreen,
        "hashtags": tags,
    }


def build_script():
    scripts = _load_scripts()
    last_idx = _load_last_index()

    indices = list(range(len(scripts)))
    if last_idx in indices and len(indices) > 1:
        indices.remove(last_idx)

    idx = random.choice(indices)
    _save_last_index(idx)

    return _normalize_candidate(scripts[idx])
