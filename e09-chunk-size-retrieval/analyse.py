"""Score rankings from every retriever that has results, plus the model-free boundary count.

Usage: python analyse.py [--boot 2000]
Writes analysis/boundaries.json, analysis/<retriever>.json, analysis/FULL-RESULTS.md.
"""
from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict

from chunking import chunk, configs
from common import ANALYSIS, BUDGETS, DATA, RESULTS, SEED, TOP_K, read_jsonl, write_json
from keyfact import carries_place, place_range
from scoring import intact_anywhere, outcome

LABELS = ("found", "partial", "missed", "cut")


def load():
    contracts = {c["contract_id"]: c["text"] for c in read_jsonl(DATA / "contracts.jsonl")}
    items = read_jsonl(DATA / "items.jsonl")
    chunks = {(n, cid): chunk(t, cfg) for n, cfg in configs().items() for cid, t in contracts.items()}
    return contracts, items, chunks


def cluster_ci(values_by_contract: dict[str, list[int]], boot: int, rng: random.Random) -> list[float]:
    """95% interval for a proportion, resampling whole contracts (questions in one contract are correlated)."""
    keys = list(values_by_contract)
    stats = []
    for _ in range(boot):
        hit = n = 0
        for k in (rng.choice(keys) for _ in keys):
            v = values_by_contract[k]
            hit += sum(v)
            n += len(v)
        stats.append(hit / n)
    stats.sort()
    return [round(stats[int(0.025 * boot)], 4), round(stats[int(0.975 * boot) - 1], 4)]


def boundaries(items, chunks, contracts):
    """Model-free: share of questions whose every answer span is cut by a chunk boundary."""
    out = {}
    for name in configs():
        cut = [i for i in items if not intact_anywhere(chunks[(name, i["contract_id"])], i["gold_spans"])]
        n_chunks = sum(len(chunks[(name, c)]) for c in contracts)
        by_cat = Counter(i["category"] for i in cut)
        out[name] = {"questions": len(items), "no_intact_answer": len(cut), "chunks": n_chunks,
                     "no_intact_by_category": dict(sorted(by_cat.items()))}
    return out


def score(retriever, items, chunks, boot):
    path = RESULTS / retriever / "rankings.jsonl"
    rankings = {(r["config"], r["item_id"]): r["top"] for r in read_jsonl(path)}
    rng = random.Random(SEED)
    res = {}
    for name in configs():
        per_k = {}
        for k in TOP_K:
            counts = Counter()
            words = []
            by_contract = defaultdict(list)
            by_cat = defaultdict(Counter)
            rows = []
            for it in items:
                ch = chunks[(name, it["contract_id"])]
                top_idx = rankings[(name, it["item_id"])][:k]
                top = [ch[i] for i in top_idx]
                lab = outcome(top, ch, it["gold_spans"], TEXT[it["contract_id"]])
                counts[lab] += 1
                by_cat[it["category"]][lab] += 1
                by_contract[it["contract_id"]].append(1 if lab == "found" else 0)
                words.append(sum(len(TEXT[it["contract_id"]][s:e].split()) for s, e in top))
                rows.append({"item_id": it["item_id"], "outcome": lab})
            words.sort()
            per_k[str(k)] = {
                "counts": {l: counts[l] for l in LABELS},
                "found_rate": round(counts["found"] / len(items), 4),
                "found_ci95_by_contract": cluster_ci(by_contract, boot, rng),
                "median_words_to_model": words[len(words) // 2],
                "by_category": {c: {l: v[l] for l in LABELS} for c, v in sorted(by_cat.items())},
                "rows": rows,
            }
        per_b = {}
        for budget in BUDGETS:
            counts = Counter()
            by_contract = defaultdict(list)
            by_cat = defaultdict(Counter)
            ks = []
            for it in items:
                ch = chunks[(name, it["contract_id"])]
                top, used = [], 0
                for i in rankings[(name, it["item_id"])]:
                    n = len(TEXT[it["contract_id"]][ch[i][0]:ch[i][1]].split())
                    if top and used + n > budget:
                        break
                    top.append(ch[i])
                    used += n
                ks.append(len(top))
                TOPS[(name, budget, it["item_id"])] = top
                lab = outcome(top, ch, it["gold_spans"], TEXT[it["contract_id"]])
                counts[lab] += 1
                by_cat[it["category"]][lab] += 1
                by_contract[it["contract_id"]].append(1 if lab == "found" else 0)
            ks.sort()
            # Governing Law: is the jurisdiction named in what the model receives?
            gl_named = gl_total = gl_strict = 0
            for it in items:
                if it["category"] != "Governing Law":
                    continue
                t = TEXT[it["contract_id"]]
                places = [p for p in (place_range(t, sp) for sp in it["gold_spans"]) if p]
                if not places:
                    continue
                gl_total += 1
                gl_named += any(carries_place(TOPS[(name, budget, it["item_id"])], p) for p in places)
                gl_strict += outcome(TOPS[(name, budget, it["item_id"])], chunks[(name, it["contract_id"])], it["gold_spans"], t) == "found"
            per_b[str(budget)] = {"governing_law": {"questions": gl_total, "jurisdiction_named": gl_named, "complete_span": gl_strict},"counts": {l: counts[l] for l in LABELS},
                                  "found_rate": round(counts["found"] / len(items), 4),
                                  "found_ci95_by_contract": cluster_ci(by_contract, boot, rng),
                                  "median_chunks": ks[len(ks) // 2],
                                  "by_category": {c: {l: v[l] for l in LABELS} for c, v in sorted(by_cat.items())}}
        res[name] = {"top_k": per_k, "budget": per_b}
    return res


TEXT: dict[str, str] = {}
TOPS: dict = {}
TOPS_BY: dict = {}


def report(bounds, scored, paired_all=None) -> str:
    L = ["# E09 measured results", "",
         "Counts are questions (334 questions over 60 CUAD contracts). Retrieval searches only the chunks of the question's own contract.",
         "Found = a retrieved chunk holds a complete expert-marked answer span. Intervals resample whole contracts.", "",
         "## Answers cut by chunk boundaries (no model involved)", "",
         "| Setting | Chunks | Questions with no complete answer in any chunk |", "|---|---|---|"]
    for n, b in bounds.items():
        L.append(f"| {n} | {b['chunks']} | {b['no_intact_answer']} of {b['questions']} |")
    for r, res in scored.items():
        L += ["", f"## {r}: same reading budget", "", "The top-ranked chunks are passed until the next one would exceed the budget (at least one chunk).", "",
              "| Setting | Budget (words) | Found | Partial | Missed | Cut | Found 95% CI | Median chunks |", "|---|---|---|---|---|---|---|---|"]
        for n, v in res.items():
            for b, x in v["budget"].items():
                c = x["counts"]
                lo, hi = x["found_ci95_by_contract"]
                L.append(f"| {n} | {b} | {c['found']} | {c['partial']} | {c['missed']} | {c['cut']} | {lo:.0%}–{hi:.0%} | {x['median_chunks']} |")
        L += ["", f"## {r}: complete answers by clause type at 1,000 words", "",
              "| Clause | Questions | " + " | ".join(res) + " |", "|---|---|" + "---|" * len(res)]
        first = next(iter(res.values()))["budget"]["1000"]["by_category"]
        for cat in first:
            n = sum(first[cat].values())
            L.append(f"| {cat} | {n} | " + " | ".join(str(v["budget"]["1000"]["by_category"][cat]["found"]) for v in res.values()) + " |")
        L += ["", f"## {r}: Governing Law, is the place named in what the model receives?", "",
              "| Setting | Budget | Questions | Jurisdiction named | Complete span |", "|---|---|---|---|---|"]
        for n, v in res.items():
            for b, x in v["budget"].items():
                g = x["governing_law"]
                L.append(f"| {n} | {b} | {g['questions']} | {g['jurisdiction_named']} | {g['complete_span']} |")
        L += ["", f"## {r}: top k", "", "| Setting | k | Found | Partial | Missed | Cut | Found 95% CI | Median words to model |", "|---|---|---|---|---|---|---|---|"]
        for n, v0 in res.items():
            for k, v in v0["top_k"].items():
                c = v["counts"]
                lo, hi = v["found_ci95_by_contract"]
                L.append(f"| {n} | {k} | {c['found']} | {c['partial']} | {c['missed']} | {c['cut']} | {lo:.0%}–{hi:.0%} | {v['median_words_to_model']} |")
    for r, pr in (paired_all or {}).items():
        L += ["", f"## {r}: paragraph-aware 256 against each setting at 1,000 words, question by question", "",
              "| Other setting | Only para-256 found | Only other found | Net | Net 95% CI (contracts resampled) |", "|---|---|---|---|---|"]
        for n, v in pr.items():
            lo, hi = v["net_ci95_by_contract"]
            L.append(f"| {n} | {v['only_para-256']} | {v['only_other']} | {v['net']:+d} | {lo:+d} to {hi:+d} |")
    L += ["", "## Limits", "",
          "- One public contract set (CUAD, US commercial contracts filed with the SEC). Ten clause types, with fixed plain-English questions.",
          "- An expert span marks where a lawyer looked, not the only text that could answer the question; a chunk can be useful without holding the whole span.",
          "- Questions inside one contract are correlated, so intervals resample contracts, not questions.",
          "- BM25 is keyword search. Embedding results come from separate runs on the author's PC."]
    return "\n".join(L) + "\n"


def paired(retriever, items, chunks, boot, base="para-256", budget=1000):
    """Paragraph-aware 256 against every other setting at the same budget, question by question.

    Reuses the top lists from score(); TOPS holds the last retriever scored, so call right after it.
    """
    out = {}
    rng = random.Random(SEED + 1)
    for name in configs():
        if name == base:
            continue
        by_contract = defaultdict(list)
        only_base = only_other = 0
        for it in items:
            t = TEXT[it["contract_id"]]
            x = outcome(TOPS_BY[retriever][(base, budget, it["item_id"])], chunks[(base, it["contract_id"])], it["gold_spans"], t) == "found"
            y = outcome(TOPS_BY[retriever][(name, budget, it["item_id"])], chunks[(name, it["contract_id"])], it["gold_spans"], t) == "found"
            only_base += x and not y
            only_other += y and not x
            by_contract[it["contract_id"]].append(int(x) - int(y))
        keys = list(by_contract)
        diffs = []
        for _ in range(boot):
            tot = 0
            for k in (rng.choice(keys) for _ in keys):
                tot += sum(by_contract[k])
            diffs.append(tot)
        diffs.sort()
        out[name] = {"budget": budget, f"only_{base}": only_base, "only_other": only_other,
                     "net": only_base - only_other, "net_ci95_by_contract": [diffs[int(0.025 * boot)], diffs[int(0.975 * boot) - 1]]}
    return out


def examples(items, chunks, a="fixed-256", b="para-256", budget=1000):
    tops = TOPS_BY["bm25"]
    """Questions where fixed chunks cut the clause but paragraph-aware chunks kept it whole (BM25, 1,000 words).

    For each: the part of the clause the model received and the part it did not.
    """
    out = []
    for it in items:
        if it["category"] not in ("Renewal Term", "Notice Period To Terminate Renewal", "Cap On Liability", "Termination For Convenience"):
            continue
        top_a, top_b = tops[(a, budget, it["item_id"])], tops[(b, budget, it["item_id"])]
        ch = chunks[(a, it["contract_id"])]
        t = TEXT[it["contract_id"]]
        if outcome(top_a, ch, it["gold_spans"], t) != "partial" or outcome(top_b, chunks[(b, it["contract_id"])], it["gold_spans"], t) != "found":
            continue
        t = TEXT[it["contract_id"]]
        s, e = it["gold_spans"][0]
        got = [(max(s, c0), min(e, c1)) for c0, c1 in top_a if c0 < e and s < c1]
        if not got:
            continue
        received = " ".join(" ".join(t[x:y].split()) for x, y in got)
        missing_ranges, pos = [], s
        for x, y in sorted(got):
            if x > pos:
                missing_ranges.append((pos, x))
            pos = max(pos, y)
        if pos < e:
            missing_ranges.append((pos, e))
        out.append({"item_id": it["item_id"], "category": it["category"], "question": it["question"],
                    "clause": " ".join(t[s:e].split()), "received_with_fixed_256": received,
                    "not_received": " ... ".join(" ".join(t[x:y].split()) for x, y in missing_ranges)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    contracts, items, chunks = load()
    TEXT.update(contracts)
    bounds = boundaries(items, chunks, contracts)
    write_json(ANALYSIS / "boundaries.json", bounds)
    scored = {}
    for r in sorted(p.name for p in RESULTS.iterdir() if (p / "rankings.jsonl").exists()):
        TOPS.clear()
        scored[r] = score(r, items, chunks, a.boot)
        TOPS_BY[r] = dict(TOPS)
        write_json(ANALYSIS / f"{r}.json", scored[r])
    if "bm25" in scored:
        write_json(ANALYSIS / "examples.json", examples(items, chunks))
    paired_all = {r: paired(r, items, chunks, a.boot) for r in scored}
    write_json(ANALYSIS / "paired.json", paired_all)
    (ANALYSIS / "FULL-RESULTS.md").write_text(report(bounds, scored, paired_all), encoding="utf-8", newline="\n")
    print("retrievers:", ", ".join(scored) or "none")


if __name__ == "__main__":
    main()
