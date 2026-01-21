import json
import os
import random

SCRIPTS_PATH = os.path.join("data", "scripts.json")

# Fallback por si no existe data/scripts.json
FALLBACK = [
    {
        "title": "AN UNCOMFORTABLE TRUTH",
        "script": "Most people don't fear failure. They fear realization: "
                  "that they're replaceable. Comfort feels safe—until it traps you.",
        "onscreen_text": "MOST PEOPLE DON'T FEAR FAILURE.\nTHEY FEAR BEING REPLACEABLE.",
        "hashtags": ["psychology", "mindset", "truth"]
    }
]

def _load_scripts():
    """
    Carga candidatos desde data/scripts.json.
    Soporta 2 formatos:
      A) lista de objetos: [ {...}, {...} ]
      B) objeto con key 'items': { "items": [ {...} ] }
    """
    if not os.path.exists(SCRIPTS_PATH):
        return FALLBACK

    with open(SCRIPTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = data.get("items") or data.get("scripts") or data.get("data") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []

    if not items:
        return FALLBACK

    return items

def _normalize_candidate(raw):
    """
    Normaliza llaves para que main.py SIEMPRE encuentre:
      title, script, onscreen_text, hashtags
    """
    c = dict(raw) if isinstance(raw, dict) else {}

    # title
    title = c.get("title") or c.get("hook") or c.get("headline") or "AN UNCOMFORTABLE TRUTH"
    title = str(title).strip().upper()  # TU requisito: MAYÚSCULAS

    # script (lo que va a narrar la voz)
    script = c.get("script") or c.get("narration") or c.get("voiceover") or c.get("text") or ""
    script = str(script).strip()
    if not script:
        script = FALLBACK[0]["script"]

    # onscreen_text (texto en pantalla; debe concordar con el script)
    onscreen = c.get("onscreen_text") or c.get("subtitle") or c.get("caption") or c.get("text_on_screen")
    if onscreen is None or str(onscreen).strip() == "":
        # Si no existe, lo derivamos del script (1–2 líneas máximas)
        s = script.replace("\n", " ").strip()
        # Recorta a algo corto y potente
        onscreen = s[:90].upper()
        # Divide en 2 líneas si es largo
        if len(onscreen) > 45:
            onscreen = onscreen[:45].rstrip() + "\n" + onscreen[45:90].lstrip()
    else:
        onscreen = str(onscreen).strip().upper()

    # hashtags (main.py espera lista)
    tags = c.get("hashtags") or c.get("tags") or c.get("hashtag") or []
    if isinstance(tags, str):
        # permite "psychology mindset truth"
        tags = [t.strip("# ").strip() for t in tags.replace(",", " ").split() if t.strip()]
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip("# ").strip() for t in tags if str(t).strip()]
    if not tags:
        tags = ["psychology", "mindset", "truth"]

    return {
        "title": title,
        "script": script,
        "onscreen_text": onscreen,
        "hashtags": tags,
    }

def build_script():
    """
    Devuelve un dict compatible con main.py:
    {
      "title": str,
      "script": str,
      "onscreen_text": str,
      "hashtags": list[str]
    }
    """
    scripts = _load_scripts()
    picked = random.choice(scripts)
    return _normalize_candidate(picked)
