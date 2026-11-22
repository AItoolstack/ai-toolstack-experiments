"""Select contracts and build questions from CUAD v1.

Usage: python build_items.py path/to/CUADv1.json

CUAD (The Atticus Project, Hendrycks et al. 2021) is licensed CC BY 4.0.
Source: https://github.com/TheAtticusProject/cuad (data.zip, sha256 below).
Writes data/contracts.jsonl and data/items.jsonl.
"""
from __future__ import annotations

import random
import re
import sys
from pathlib import Path

from common import DATA, MIN_WORDS, N_CONTRACTS, QUESTIONS, SEED, write_jsonl

DATA_ZIP_SHA256 = "f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a"
CAT_RE = re.compile(r'related to "([^"]+)"')


def build(cuad: dict) -> tuple[list[dict], list[dict]]:
    docs = cuad["data"]
    eligible = [d for d in docs if len(d["paragraphs"][0]["context"].split()) >= MIN_WORDS]
    eligible.sort(key=lambda d: d["title"])
    rng = random.Random(SEED)
    chosen = rng.sample(eligible, N_CONTRACTS)
    chosen.sort(key=lambda d: d["title"])

    contracts, items = [], []
    for ci, d in enumerate(chosen):
        cid = f"c{ci:02d}"
        text = d["paragraphs"][0]["context"]
        contracts.append({"contract_id": cid, "cuad_title": d["title"], "words": len(text.split()), "text": text})
        for qa in d["paragraphs"][0]["qas"]:
            cat = CAT_RE.search(qa["question"]).group(1)
            if cat not in QUESTIONS or not qa["answers"]:
                continue
            spans = []
            for a in qa["answers"]:
                s, e = a["answer_start"], a["answer_start"] + len(a["text"])
                if text[s:e] != a["text"]:
                    raise ValueError(f"offset mismatch in {d['title']} / {cat}")
                spans.append([s, e])
            spans = sorted({tuple(x) for x in spans})
            items.append({
                "item_id": f"{cid}-{list(QUESTIONS).index(cat):02d}",
                "contract_id": cid,
                "category": cat,
                "question": QUESTIONS[cat],
                "gold_spans": [list(x) for x in spans],
                "gold_words": [len(text[s:e].split()) for s, e in spans],
            })
    return contracts, items


def main() -> None:
    import json

    src = Path(sys.argv[1])
    cuad = json.loads(src.read_text(encoding="utf-8"))
    contracts, items = build(cuad)
    write_jsonl(DATA / "contracts.jsonl", contracts)
    write_jsonl(DATA / "items.jsonl", items)
    print(f"{len(contracts)} contracts, {len(items)} questions")


if __name__ == "__main__":
    main()
