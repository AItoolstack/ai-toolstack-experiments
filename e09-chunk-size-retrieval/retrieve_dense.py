"""Rank chunks with an embedding model (cosine similarity), for every chunking setting.

Usage:
  python retrieve_dense.py --model local            # all-MiniLM-L6-v2 on CPU, free, downloads ~90 MB once
  python retrieve_dense.py --model openai --estimate
  python retrieve_dense.py --model openai --yes      # text-embedding-3-small, needs OPENAI_API_KEY in .env
  python retrieve_dense.py --model fake              # hashed word counts, no download; tests the pipeline only

Embeddings are cached in results/<model>/cache/, so a rerun never pays twice for the same text.
Writes results/<model>/rankings.jsonl and manifest.json.
"""
from __future__ import annotations

import argparse
import array
import base64
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

from chunking import chunk, configs
from common import DATA, HERE, KEEP_RANKED, QUESTIONS, RESULTS, read_jsonl, write_json, write_jsonl, tokenize

MODELS = {
    "local": "sentence-transformers/all-MiniLM-L6-v2",
    "openai": "text-embedding-3-small",
    "fake": "hashed-bag-of-words-256",
}
OPENAI_PRICE_PER_M = 0.02  # USD per million input tokens, list price; recheck before running


def key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Cache:
    def __init__(self, folder: Path):
        self.path = folder / "cache" / "embeddings.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.vec: dict[str, bytes] = {}
        if self.path.exists():
            for line in self.path.open(encoding="utf-8"):
                r = json.loads(line)
                self.vec[r["k"]] = base64.b64decode(r["v"])

    def add(self, pairs: list[tuple[str, list[float]]]) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            for k, v in pairs:
                self.vec[k] = array.array("f", v).tobytes()
                f.write(json.dumps({"k": k, "v": base64.b64encode(array.array("f", v).tobytes()).decode()}) + "\n")


def unit_vector(b: bytes):
    import numpy as np  # noqa: PLC0415

    v = np.frombuffer(b, dtype=np.float32)
    return v / (np.linalg.norm(v) or 1.0)


def embed_fake(texts: list[str]) -> list[list[float]]:
    out = []
    for t in texts:
        v = [0.0] * 256
        for w in tokenize(t):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1.0
        out.append(v)
    return out


def embed_local(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    global _ST
    if "_ST" not in globals():
        _ST = SentenceTransformer(MODELS["local"], device="cpu")
    return _ST.encode(texts, batch_size=64, show_progress_bar=False).tolist()


def load_env() -> None:
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def embed_openai(texts: list[str]) -> list[list[float]]:
    body = json.dumps({"model": MODELS["openai"], "input": texts}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/embeddings", data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())["data"]
            return [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
        except Exception:  # noqa: BLE001
            if attempt == 4:
                raise
            time.sleep(2 ** attempt * 2)
    raise RuntimeError("unreachable")


def batches(texts: list[str], max_items: int, max_words: int):
    cur, words = [], 0
    for t in texts:
        n = len(t.split())
        if cur and (len(cur) >= max_items or words + n > max_words):
            yield cur
            cur, words = [], 0
        cur.append(t)
        words += n
    if cur:
        yield cur


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm a paid run")
    a = ap.parse_args()

    contracts = {c["contract_id"]: c["text"] for c in read_jsonl(DATA / "contracts.jsonl")}
    items = read_jsonl(DATA / "items.jsonl")
    plan = {(n, cid): chunk(t, cfg) for n, cfg in configs().items() for cid, t in contracts.items()}
    texts = {key(contracts[cid][s:e]): contracts[cid][s:e] for (n, cid), ch in plan.items() for s, e in ch}
    for q in QUESTIONS.values():
        texts[key(q)] = q

    out = RESULTS / a.model
    cache = Cache(out)
    todo = [t for k, t in texts.items() if k not in cache.vec]
    words = sum(len(t.split()) for t in todo)
    est_tokens = int(words * 1.35)
    print(f"{len(texts)} unique texts, {len(todo)} not cached, ~{words:,} words (~{est_tokens:,} tokens)")
    if a.model == "openai":
        print(f"estimated cost at ${OPENAI_PRICE_PER_M}/M tokens: ${est_tokens / 1e6 * OPENAI_PRICE_PER_M:.2f}")
        if a.estimate:
            return
        if not a.yes:
            raise SystemExit("paid run: add --yes after checking the estimate")
        load_env()
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY missing (put it in e09-chunk-size-retrieval/.env)")
    if a.estimate:
        return

    fn = {"fake": embed_fake, "local": embed_local, "openai": embed_openai}[a.model]
    max_items, max_words = (64, 10**9) if a.model != "openai" else (256, 150_000)
    started = time.time()
    for i, b in enumerate(batches(todo, max_items, max_words)):
        cache.add([(key(t), v) for t, v in zip(b, fn(b))])
        if i % 20 == 0:
            print(f"  embedded {len(cache.vec):,}/{len(texts):,}")
    seconds = round(time.time() - started, 1)

    import numpy as np  # noqa: PLC0415

    rows = []
    for (name, cid), ch in plan.items():
        cmat = np.stack([unit_vector(cache.vec[key(contracts[cid][s:e])]) for s, e in ch])
        for it in (i for i in items if i["contract_id"] == cid):
            sims = (cmat @ unit_vector(cache.vec[key(it["question"])])).tolist()
            order = sorted(range(len(sims)), key=lambda i: (-sims[i], i))[:KEEP_RANKED]
            rows.append({"config": name, "item_id": it["item_id"], "top": order})
    write_jsonl(out / "rankings.jsonl", rows)
    manifest = {"retriever": a.model, "model": MODELS[a.model], "unique_texts": len(texts), "rows": len(rows),
                "embed_seconds_this_run": seconds, "words_embedded_this_run": words}
    if a.model == "local":
        manifest["note"] = "all-MiniLM-L6-v2 reads at most 256 word pieces (~190 words); longer chunks are truncated"
        try:
            import sentence_transformers  # noqa: PLC0415
            manifest["sentence_transformers"] = sentence_transformers.__version__
        except ImportError:
            pass
    write_json(out / "manifest.json", manifest)
    print(f"{a.model}: {len(rows)} rankings")


if __name__ == "__main__":
    main()
