"""Three ways to find the articles that answer a question, all returning article ids, best first.

  bm25        keyword ranking (standard library)
  embeddings  semantic similarity with a local multilingual model (fastembed, runs on CPU, no API)
  hibrida     both rankings merged by reciprocal rank fusion
"""

import hashlib
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE = Path(__file__).resolve().parent.parent / ".cache"
STOP = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas", "um", "uma", "para", "por", "com",
    "que", "se", "ao", "aos", "ou", "ser", "pelo", "pela", "sobre", "como", "qual", "quais", "quando", "onde", "quem",
    "meu", "minha", "meus", "minhas", "seu", "sua", "lei",
}  # compared after accents are stripped, so "à" and "é" are already "a" and "e"


def tokens(text):
    t = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in STOP and len(w) > 1]


def by_article(chunk_ids_scores, chunks, k):
    """Best chunk score per article, top k article ids."""
    best = {}
    for i, s in chunk_ids_scores:
        a = chunks[i]["art"]
        if a not in best or s > best[a]:
            best[a] = s
    return [a for a, _ in sorted(best.items(), key=lambda x: -x[1])[:k]]


class BM25:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks = chunks
        self.docs = [Counter(tokens(c["text"])) for c in chunks]
        self.len = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(w for d in self.docs for w in d)
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query):
        q = tokens(query)
        out = []
        for i, (d, dl) in enumerate(zip(self.docs, self.len)):
            s = sum(self.idf[w] * d[w] * (self.k1 + 1) / (d[w] + self.k1 * (1 - self.b + self.b * dl / self.avg)) for w in q if w in d)
            out.append((i, s))
        return out

    def search(self, query, k=5):
        return by_article(self.scores(query), self.chunks, k)


class Embeddings:
    """Chunk vectors are computed once and cached on disk, keyed by model and text."""

    def __init__(self, chunks, embed=None):
        import numpy as np

        self.np, self.chunks = np, chunks
        if embed is None:
            from fastembed import TextEmbedding

            model = TextEmbedding(MODEL)
            # small batches: the default (256) pads every chunk to the longest one and peaks at ~3 GB
            embed = lambda texts: np.array(list(model.embed(texts, batch_size=8)))
        self.embed = embed
        texts = [c["text"] for c in chunks]
        key = hashlib.sha256((MODEL + "\n".join(texts)).encode()).hexdigest()[:16]
        path = CACHE / f"emb-{key}.npy"
        if path.exists():
            vecs = np.load(path)
        else:
            vecs = embed(texts)
            CACHE.mkdir(exist_ok=True)
            np.save(path, vecs)
        self.vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    def scores(self, query):
        q = self.embed([query])[0]
        sims = self.vecs @ (q / self.np.linalg.norm(q))  # cosine similarity
        return list(enumerate(sims.tolist()))

    def search(self, query, k=5):
        return by_article(self.scores(query), self.chunks, k)


class Hybrid:
    """Reciprocal rank fusion: score = sum of 1 / (60 + rank) over both rankings. No score scaling needed."""

    def __init__(self, *engines, depth=20):
        self.engines, self.depth = engines, depth

    def search(self, query, k=5):
        fused = Counter()
        for e in self.engines:
            for rank, art in enumerate(e.search(query, self.depth)):
                fused[art] += 1 / (60 + rank)
        return [a for a, _ in fused.most_common(k)]
