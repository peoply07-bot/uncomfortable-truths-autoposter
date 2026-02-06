import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PATH = "data/history.json"


def load_history():
    if not os.path.exists(PATH):
        return []
    with open(PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history):
    os.makedirs("data", exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def accept_candidate(c, history, threshold=0.65):
    """
    Devuelve True si el candidato es suficientemente distinto.
    Reglas duras + similitud semántica.
    """
    if not history:
        return True

    last = history[-1]

    # 🚫 Bloqueo duro: mismo título
    if c["title"].strip().lower() == last["title"].strip().lower():
        return False

    # 🚫 Bloqueo duro: mismo script exacto
    if c["script"].strip().lower() == last["script"].strip().lower():
        return False

    texts = [h["script"] for h in history[-5:]]
    corpus = texts + [c["script"]]

    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    ).fit_transform(corpus)

    sims = cosine_similarity(tfidf[-1], tfidf[:-1])

    return sims.max() < threshold
