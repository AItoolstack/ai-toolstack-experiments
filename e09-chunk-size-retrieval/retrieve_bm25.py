"""Rank every contract's chunks for every question with BM25, for every chunking setting.

Writes results/bm25/rankings.jsonl: one row per (config, item) with the top chunk indices.
"""
from __future__ import annotations

from bm25 import BM25, rank
from chunking import chunk, configs
from common import DATA, KEEP_RANKED, RESULTS, read_jsonl, write_json, write_jsonl


def main() -> None:
    contracts = {c["contract_id"]: c["text"] for c in read_jsonl(DATA / "contracts.jsonl")}
    items = read_jsonl(DATA / "items.jsonl")
    rows = []
    for name, cfg in configs().items():
        for cid, text in contracts.items():
            chunks = chunk(text, cfg)
            index = BM25([text[s:e] for s, e in chunks])
            for it in (i for i in items if i["contract_id"] == cid):
                rows.append({"config": name, "item_id": it["item_id"], "top": rank(index.scores(it["question"]))[:KEEP_RANKED]})
    out = RESULTS / "bm25"
    write_jsonl(out / "rankings.jsonl", rows)
    write_json(out / "manifest.json", {"retriever": "bm25", "k1": 1.5, "b": 0.75, "tokenizer": "lowercase [a-z0-9]+", "rows": len(rows)})
    print(f"bm25: {len(rows)} rankings")


if __name__ == "__main__":
    main()
