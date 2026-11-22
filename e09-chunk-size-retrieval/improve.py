"""E9b: can common retrieval methods get the complete clause to the model for 90% of questions?

Starts from E9's best setting (paragraph-aware chunks up to 256 words, BM25) and adds one method at a time.
Methods are chosen on 20 "dev" contracts; the headline numbers are reported on the other 40 "test"
contracts, which were not looked at while choosing.

Usage: python improve.py [--boot 2000]
Reads results/<method>/rankings.jsonl for methods run on Tej's PC (hybrid, rerank, contextual), if present.
Writes analysis/improve.json and analysis/IMPROVE-RESULTS.md.
"""
from __future__ import annotations

import argparse
import random
import re
from collections import defaultdict

from bm25 import BM25, rank
from chunking import fixed, paragraph_aware
from common import ANALYSIS, DATA, RESULTS, SEED, read_jsonl, write_json
from scoring import outcome

BUDGETS = (1000, 2000)
PARENT_SIZE = 256
CHILD_SIZE, CHILD_OVERLAP = 64, 12

# Contract vocabulary added to each question. Written from general contract wording before any E9b run,
# not from reading the test contracts.
EXPANSIONS = {
    "Governing Law": "governed governing laws law construed jurisdiction",
    "Expiration Date": "term initial term expire expiration years period until terminate",
    "Renewal Term": "renew renewal renewed automatically successive extend extension term",
    "Notice Period To Terminate Renewal": "renew renewal non-renewal notice prior days written expiration term",
    "Termination For Convenience": "terminate termination convenience without cause any reason notice days",
    "Anti-Assignment": "assign assignment assigned transfer consent successor delegate",
    "Change Of Control": "change of control merger acquisition acquired control substantially all assets",
    "Cap On Liability": "liability limitation exceed aggregate damages consequential limit maximum",
    "Non-Compete": "compete competing competitive competitor non-compete exclusive restrict",
    "Audit Rights": "audit inspect inspection books records examine accountant",
}

LABEL_RE = re.compile(
    r"^\s*(?:(?:Section|SECTION|Article|ARTICLE)\s+)?"
    r"(?P<num>[0-9]{1,2}(?:\.[0-9]{1,2}){0,2}|[IVXLC]{1,6})\.?\s+"
    r"(?P<title>[A-Z][A-Za-z'&/,\- ]{2,70}?)(?:\.(?=\s|$)|\s*$)")


def split_contracts(ids: list[str]) -> tuple[set[str], set[str]]:
    rng = random.Random(SEED + 1)
    dev = set(rng.sample(sorted(ids), 20))
    return dev, set(ids) - dev


def headings(text: str) -> list[tuple[int, str]]:
    """(position, heading path) at each numbered heading, inline or on its own line.

    The path keeps the top-level section with the current sub-clause, e.g. "10 Term and Termination > 10.1 Renewal".
    Titles longer than 8 words are treated as body text, not headings.
    """
    out, pos, top = [], 0, ""
    for line in text.split("\n"):
        m = LABEL_RE.match(line)
        if m and len(m.group("title").split()) <= 8 and "confidential" not in line.lower():
            label = f"{m.group('num')} {' '.join(m.group('title').split())}"
            if "." not in m.group("num"):
                top = label
                out.append((pos, top))
            else:
                out.append((pos, f"{top} > {label}" if top else label))
        pos += len(line) + 1
    return out


def header_for(heads: list[tuple[int, str]], start: int) -> str:
    last = ""
    for p, h in heads:
        if p > start:
            break
        last = h
    return last


def fill(order: list[tuple[int, int]], text: str, budget: int, extra_words: dict | None = None) -> list[tuple[int, int]]:
    out, used, seen = [], 0, set()
    for c in order:
        if c in seen:
            continue
        n = len(text[c[0]:c[1]].split()) + (extra_words or {}).get(c, 0)
        if out and used + n > budget:
            break
        out.append(c)
        seen.add(c)
        used += n
    return out


def run_methods(contracts, items):
    """Returns {method: {(item_id, budget): passed chunk ranges}}."""
    passed = defaultdict(dict)
    pc_rankings = {}
    for name in ("rewrite", "hybrid", "rerank", "contextual"):
        p = RESULTS / name / "rankings.jsonl"
        if p.exists():
            pc_rankings[name] = {r["item_id"]: r["top"] for r in read_jsonl(p) if r["config"] == "para-256"}

    for cid, text in contracts.items():
        parents = paragraph_aware(text, PARENT_SIZE)
        heads = headings(text)
        hdr = [header_for(heads, s) for s, _ in parents]
        plain = BM25([text[s:e] for s, e in parents])
        headed = BM25([f"{h}\n{text[s:e]}" for h, (s, e) in zip(hdr, parents)])
        hdr_words = {c: len(h.split()) for c, h in zip(parents, hdr)}
        children = fixed(text, CHILD_SIZE, CHILD_OVERLAP)
        kids = BM25([text[s:e] for s, e in children])
        parent_of = []
        for s, e in children:
            mid = (s + e) // 2
            parent_of.append(next((p for p in parents if p[0] <= mid < p[1]), next(p for p in parents if p[1] >= s)))

        for it in (i for i in items if i["contract_id"] == cid):
            q = it["question"]
            qx = q + " " + EXPANSIONS[it["category"]]
            orders = {
                "baseline": [parents[i] for i in rank(plain.scores(q))],
                "headers": [parents[i] for i in rank(headed.scores(q))],
                "expansion": [parents[i] for i in rank(plain.scores(qx))],
                "small-to-big": [parent_of[i] for i in rank(kids.scores(q))],
                "headers+expansion": [parents[i] for i in rank(headed.scores(qx))],
                "small-to-big+expansion": [parent_of[i] for i in rank(kids.scores(qx))],
            }
            for name, rk in pc_rankings.items():
                if it["item_id"] in rk:
                    orders[name] = [parents[i] for i in rk[it["item_id"]]]
            for m, order in orders.items():
                extra = hdr_words if m.startswith("headers") else None
                for b in BUDGETS:
                    passed[m][(it["item_id"], b)] = fill(order, text, b, extra)
            whole = [(0, len(text))]
            for b in BUDGETS:
                passed["whole contract"][(it["item_id"], b)] = whole
    return passed


def summarise(passed, items, contracts, part: set[str], boot: int):
    rng = random.Random(SEED + 2)
    res = {}
    for m, rows in passed.items():
        if not any((it["item_id"], BUDGETS[0]) in rows for it in items if it["contract_id"] in part):
            continue
        res[m] = {}
        for b in BUDGETS:
            by_c = defaultdict(list)
            n_found = 0
            words = []
            for it in items:
                if it["contract_id"] not in part or (it["item_id"], b) not in rows:
                    continue
                t = contracts[it["contract_id"]]
                top = rows[(it["item_id"], b)]
                f = outcome(top, [], it["gold_spans"], t) == "found"
                n_found += f
                by_c[it["contract_id"]].append(int(f))
                words.append(sum(len(t[s:e].split()) for s, e in top))
            keys = list(by_c)
            stats = []
            for _ in range(boot):
                h = n = 0
                for k in (rng.choice(keys) for _ in keys):
                    h += sum(by_c[k])
                    n += len(by_c[k])
                stats.append(h / n)
            stats.sort()
            words.sort()
            total = sum(len(v) for v in by_c.values())
            res[m][str(b)] = {"found": n_found, "questions": total, "rate": round(n_found / total, 4),
                              "ci95": [round(stats[int(0.025 * boot)], 4), round(stats[int(0.975 * boot) - 1], 4)],
                              "median_words": words[len(words) // 2]}
    return res


def report(dev, test, n_dev, n_test) -> str:
    L = ["# E9b: getting the complete clause to the model", "",
         f"Starting point: paragraph-aware chunks up to {PARENT_SIZE} words, BM25. Methods were chosen on {n_dev} dev questions (20 contracts).",
         f"Headline numbers are on {n_test} test questions (40 contracts) that were not used to choose anything.",
         "Found = the text passed to the model covers a complete expert-marked clause. Intervals resample contracts.", ""]
    for label, res in (("Test contracts (headline)", test), ("Dev contracts (used to choose)", dev)):
        L += [f"## {label}", "", "| Method | Budget (words) | Found | Rate | 95% CI | Median words passed |", "|---|---|---|---|---|---|"]
        for m, v in res.items():
            for b, x in v.items():
                lo, hi = x["ci95"]
                L.append(f"| {m} | {b} | {x['found']} of {x['questions']} | {x['rate']:.0%} | {lo:.0%}–{hi:.0%} | {x['median_words']:,} |")
        L.append("")
    L += ["## Notes", "",
          "- Whole contract: always contains the clause, by definition; the cost is the median words passed.",
          "- Headers: the nearest section heading is added to each chunk before search and counted in the budget.",
          "- Expansion: a fixed list of contract words per clause type, written before the run.",
          f"- Small-to-big: search {CHILD_SIZE}-word pieces (overlap {CHILD_OVERLAP}), pass the paragraph-aware chunk each one sits in.",
          "- Rewrite (an LLM writes the search words), hybrid, rerank and contextual appear only after the PC runs (results/<method>/rankings.jsonl). Contextual is run on the test contracts only."]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    contracts = {c["contract_id"]: c["text"] for c in read_jsonl(DATA / "contracts.jsonl")}
    items = read_jsonl(DATA / "items.jsonl")
    dev, test = split_contracts(list(contracts))
    passed = run_methods(contracts, items)
    r_dev = summarise(passed, items, contracts, dev, a.boot)
    r_test = summarise(passed, items, contracts, test, a.boot)
    n_dev = sum(i["contract_id"] in dev for i in items)
    write_json(ANALYSIS / "improve.json", {"dev_contracts": sorted(dev), "test_contracts": sorted(test), "dev": r_dev, "test": r_test})
    (ANALYSIS / "IMPROVE-RESULTS.md").write_text(report(r_dev, r_test, n_dev, len(items) - n_dev), encoding="utf-8", newline="\n")
    print("methods:", ", ".join(passed))


if __name__ == "__main__":
    main()
