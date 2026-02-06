def accept_candidate(c, history, threshold=0.65):
    if not history:
        return True

    last = history[-1]

    # BLOQUEO DURO: mismo título
    if c["title"].strip().lower() == last["title"].strip().lower():
        return False

    # BLOQUEO DURO: mismo script exacto
    if c["script"].strip().lower() == last["script"].strip().lower():
        return False

    texts = [h["script"] for h in history[-5:]]  # solo últimos 5
    corpus = texts + [c["script"]]

    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    ).fit_transform(corpus)

    sims = cosine_similarity(tfidf[-1], tfidf[:-1])

    return sims.max() < threshold
