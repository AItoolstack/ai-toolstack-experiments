"""BM25 (Okapi) over one contract's chunks. Standard library only."""
from __future__ import annotations

import math
from collections import Counter

from common import tokenize

K1 = 1.5
B = 0.75


class BM25:
    def __init__(self, docs: list[str]):
        self.toks = [tokenize(d) for d in docs]
        self.tf = [Counter(t) for t in self.toks]
        self.len = [len(t) for t in self.toks]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 0.0
        df: Counter = Counter()
        for t in self.tf:
            df.update(t.keys())
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for tf, ln in zip(self.tf, self.len):
            s = 0.0
            for w in q:
                f = tf.get(w)
                if f:
                    s += self.idf[w] * f * (K1 + 1) / (f + K1 * (1 - B + B * ln / self.avg))
            out.append(s)
        return out


def rank(scores: list[float]) -> list[int]:
    """Indices by score, highest first; ties broken by position in the document."""
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))
