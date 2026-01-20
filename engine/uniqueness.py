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

def accept_candidate(c, history, threshold=0.8):
    texts = [h["script"] for h in history]
    if not texts:
        return True

    corpus = texts + [c["script"]]
    tfidf = TfidfVectorizer(stop_words="english").fit_transform(corpus)
    sims = cosine_similarity(tfidf[-1], tfidf[:-1])
    return sims.max() < threshold
