"""E9b methods that need a model download or an API key. Run on Tej's PC, one at a time.

  python pc_methods.py rewrite --llm <chat model id>            # an LLM writes the search words (10 calls)
  python pc_methods.py hybrid                                   # BM25 + embeddings, merged; needs E9's local or openai run
  python pc_methods.py rerank                                   # local cross-encoder re-scores BM25's top 30 (free, ~90 MB)
  python pc_methods.py contextual --llm <chat model id> --estimate
  python pc_methods.py contextual --llm <chat model id> --yes   # Anthropic's contextual retrieval, test contracts only

Every method ranks the same paragraph-aware 256-word chunks, so improve.py scores them the same way.
Writes results/<method>/rankings.jsonl (and results/rewrite/rewrites.json, results/contextual/cache/).
API calls use OPENAI_API_KEY from .env (OpenAI-compatible chat endpoint; set OPENAI_BASE_URL to use another provider).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request

from bm25 import BM25, rank
from chunking import paragraph_aware
from common import DATA, QUESTIONS, RESULTS, read_jsonl, write_json, write_jsonl
from improve import split_contracts
from retrieve_dense import load_env

CONFIG = "para-256"
KEEP = 40


def chat(model: str, prompt: str, max_tokens: int = 200) -> str:
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_completion_tokens": max_tokens}).encode()
    req = urllib.request.Request(f"{base}/chat/completions", data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:  # noqa: BLE001
            if attempt == 4:
                raise
            time.sleep(2 ** attempt * 2)
    raise RuntimeError("unreachable")


def need_key() -> None:
    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY missing (put it in e09-chunk-size-retrieval/.env)")


def data():
    contracts = {c["contract_id"]: c["text"] for c in read_jsonl(DATA / "contracts.jsonl")}
    items = read_jsonl(DATA / "items.jsonl")
    chunks = {cid: paragraph_aware(t, 256) for cid, t in contracts.items()}
    return contracts, items, chunks


def save(method: str, rows: list[dict], meta: dict) -> None:
    write_jsonl(RESULTS / method / "rankings.jsonl", rows)
    write_json(RESULTS / method / "manifest.json", {"method": method, "config": CONFIG, "rows": len(rows), **meta})
    print(f"{method}: {len(rows)} rankings. Now run: python improve.py")


REWRITE_PROMPT = """You help search inside a commercial contract with a keyword search engine.
Rewrite the question below as a list of 6 to 12 words or short phrases that the relevant clause of a contract
would likely contain. Reply with the words only, separated by spaces, no explanation.

Question: {q}"""


def cmd_rewrite(a) -> None:
    need_key()
    rewrites = {q: chat(a.llm, REWRITE_PROMPT.format(q=q)) for q in QUESTIONS.values()}
    contracts, items, chunks = data()
    rows = []
    for cid, t in contracts.items():
        idx = BM25([t[s:e] for s, e in chunks[cid]])
        for it in (i for i in items if i["contract_id"] == cid):
            q = it["question"] + " " + rewrites[it["question"]]
            rows.append({"config": CONFIG, "item_id": it["item_id"], "top": rank(idx.scores(q))[:KEEP]})
    write_json(RESULTS / "rewrite" / "rewrites.json", rewrites)
    save("rewrite", rows, {"llm": a.llm, "prompt": REWRITE_PROMPT})


def rrf(*rankings: list[int], k: int = 60) -> list[int]:
    """Reciprocal rank fusion: merge rankings by summing 1 / (k + position)."""
    score: dict[int, float] = {}
    for r in rankings:
        for pos, i in enumerate(r):
            score[i] = score.get(i, 0.0) + 1.0 / (k + pos + 1)
    return sorted(score, key=lambda i: (-score[i], i))


def cmd_hybrid(a) -> None:
    dense_name = a.dense
    path = RESULTS / dense_name / "rankings.jsonl"
    if not path.exists():
        raise SystemExit(f"run E9's embeddings first: python retrieve_dense.py --model {dense_name}")
    dense = {r["item_id"]: r["top"] for r in read_jsonl(path) if r["config"] == CONFIG}
    contracts, items, chunks = data()
    rows = []
    for cid, t in contracts.items():
        idx = BM25([t[s:e] for s, e in chunks[cid]])
        for it in (i for i in items if i["contract_id"] == cid):
            kw = rank(idx.scores(it["question"]))
            rows.append({"config": CONFIG, "item_id": it["item_id"], "top": rrf(kw, dense[it["item_id"]])[:KEEP]})
    save("hybrid", rows, {"dense": dense_name, "fusion": "reciprocal rank fusion, k=60"})


def cmd_rerank(a) -> None:
    from sentence_transformers import CrossEncoder  # noqa: PLC0415

    model_id = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ce = CrossEncoder(model_id, device="cpu")
    contracts, items, chunks = data()
    rows = []
    for cid, t in contracts.items():
        texts = [t[s:e] for s, e in chunks[cid]]
        idx = BM25(texts)
        for it in (i for i in items if i["contract_id"] == cid):
            first = rank(idx.scores(it["question"]))
            pool = first[:30]
            scores = ce.predict([(it["question"], texts[i]) for i in pool])
            reranked = [i for _, i in sorted(zip(scores, pool), key=lambda x: -x[0])]
            rows.append({"config": CONFIG, "item_id": it["item_id"], "top": (reranked + first[30:])[:KEEP]})
    save("rerank", rows, {"reranker": model_id, "pool": 30, "first_stage": "bm25"})


CONTEXT_PROMPT = """<document>
{doc}
</document>
Here is the chunk we want to situate within the whole document
<chunk>
{chunk}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""


def cmd_contextual(a) -> None:
    contracts, items, chunks = data()
    _, test = split_contracts(list(contracts))
    todo = [(cid, s, e) for cid in sorted(test) for s, e in chunks[cid]]
    words = sum(len(contracts[cid].split()) + len(contracts[cid][s:e].split()) + 60 for cid, s, e in todo)
    tokens = int(words * 1.35)
    print(f"{len(todo)} chunks in the 40 test contracts; ~{tokens / 1e6:.1f}M input tokens without prompt caching")
    print(f"at ${a.price}/M input tokens: ~${tokens / 1e6 * a.price:.2f} (prompt caching, where offered, cuts most of the document cost)")
    if a.estimate:
        return
    if not a.yes:
        raise SystemExit("paid run: check the estimate, then add --yes")
    need_key()
    cache_path = RESULTS / "contextual" / "cache" / "contexts.jsonl"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ctx = {}
    if cache_path.exists():
        for line in cache_path.open(encoding="utf-8"):
            r = json.loads(line)
            ctx[r["k"]] = r["context"]
    with cache_path.open("a", encoding="utf-8", newline="\n") as f:
        for n, (cid, s, e) in enumerate(todo):
            k = hashlib.sha256(f"{a.llm}|{cid}|{s}|{e}".encode()).hexdigest()
            if k in ctx:
                continue
            ctx[k] = chat(a.llm, CONTEXT_PROMPT.format(doc=contracts[cid], chunk=contracts[cid][s:e]), 120)
            f.write(json.dumps({"k": k, "contract_id": cid, "start": s, "end": e, "context": ctx[k]}) + "\n")
            if n % 100 == 0:
                print(f"  {n}/{len(todo)}")
    rows = []
    for cid in sorted(test):
        t = contracts[cid]
        heads = [ctx[hashlib.sha256(f"{a.llm}|{cid}|{s}|{e}".encode()).hexdigest()] for s, e in chunks[cid]]
        idx = BM25([f"{h}\n{t[s:e]}" for h, (s, e) in zip(heads, chunks[cid])])
        for it in (i for i in items if i["contract_id"] == cid):
            rows.append({"config": CONFIG, "item_id": it["item_id"], "top": rank(idx.scores(it["question"]))[:KEEP]})
    save("contextual", rows, {"llm": a.llm, "prompt": "Anthropic contextual retrieval prompt", "contracts": "test only",
                              "search": "BM25 over context + chunk"})


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("rewrite")
    p.add_argument("--llm", required=True)
    p = sub.add_parser("hybrid")
    p.add_argument("--dense", default="local", choices=["local", "openai"])
    sub.add_parser("rerank")
    p = sub.add_parser("contextual")
    p.add_argument("--llm", required=True)
    p.add_argument("--price", type=float, default=0.15, help="USD per million input tokens for --llm; check the provider")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    {"rewrite": cmd_rewrite, "hybrid": cmd_hybrid, "rerank": cmd_rerank, "contextual": cmd_contextual}[a.cmd](a)


if __name__ == "__main__":
    main()
