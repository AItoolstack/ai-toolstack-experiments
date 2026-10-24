"""Summarise E01 results: consistency, accuracy, agreement between judges, cost and speed.

    python analyse.py                       # v2 (the real test)
    python analyse.py --items items_v1.jsonl  # v1 (the easy control)

Writes <results folder>/summary.json and prints a readable report.
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from collections import Counter, defaultdict

from common import DISPUTED, PRICES, PRICES_CHECKED, REPEATS, load_items, load_runs, results_dir, task_of


def summarise(rows: list[dict], items: dict[str, dict]) -> dict:
    by_item: dict[str, list[str]] = defaultdict(list)
    by_run: dict[int, dict[str, str]] = defaultdict(dict)
    for r in rows:
        if r["verdict"]:
            by_item[r["item"]].append(str(r["verdict"]))
            by_run[r["repeat"]][r["item"]] = str(r["verdict"])

    per_item = {}
    for iid, verdicts in sorted(by_item.items()):
        counts = Counter(verdicts)
        n = len(verdicts)
        top, top_n = counts.most_common(1)[0]
        per_item[iid] = {
            "task": task_of(items[iid]),
            "kind": items[iid]["kind"],
            "label": str(items[iid]["label"]).upper(),
            "counts": dict(counts),
            "most_common": top,
            "changed": len(counts) > 1,
            # chance that two runs picked at random disagree
            "pairwise_disagree": 1 - sum(k * (k - 1) for k in counts.values()) / (n * (n - 1)) if n > 1 else 0.0,
        }

    def consistency(pred) -> dict:
        sel = [v for v in per_item.values() if pred(v)]
        return {
            "items": len(sel),
            "same_every_run": sum(not v["changed"] for v in sel),
            "pairwise_disagree": st.mean(v["pairwise_disagree"] for v in sel) if sel else 0.0,
        }

    groups = {"all": consistency(lambda v: True)}
    for task in sorted({v["task"] for v in per_item.values()}):
        groups[task] = consistency(lambda v, t=task: v["task"] == t)
    for kind in sorted({v["kind"] for v in per_item.values()}):
        groups[kind] = consistency(lambda v, k=kind: v["kind"] == k)

    # Accuracy: clear items whose labels survived the audit, averaged over complete runs.
    complete = [rep for rep, d in sorted(by_run.items()) if len(d) == len(items)]
    accurate = [i for i, it in items.items() if it["kind"] == "clear" and i not in DISPUTED]
    binary = [i for i, it in items.items() if task_of(it) != "summary_score"]

    def per_run(ids: list[str], hit) -> list[float]:
        return [sum(hit(i, by_run[rep][i]) for i in ids) for rep in complete] if ids else []

    def spread(xs: list[float]) -> dict | None:
        return {"mean": st.mean(xs), "min": min(xs), "max": max(xs)} if xs else None

    right = per_run([i for i in accurate if i in binary], lambda i, v: v == items[i]["label"].upper())
    passed = per_run(binary, lambda i, v: v == "PASS")

    tok_in = sum(r.get("prompt_tokens") or 0 for r in rows)
    tok_out = sum(r.get("completion_tokens") or 0 for r in rows)
    model = rows[0].get("model", "openai/gpt-oss-120b")
    price = PRICES.get(model)
    cost = (tok_in * price[0] + tok_out * price[1]) / 1e6 if price else None
    latency = sorted(r["latency_s"] for r in rows if r.get("latency_s") is not None)
    return {
        "model": model,
        "calls": len(rows),
        "unparsed": sum(not r["verdict"] for r in rows),
        "cut_off": sum(r.get("finish_reason") == "length" for r in rows),
        "complete_runs": len(complete),
        "consistency": groups,
        "right_on_clear_pass_fail": {"of": len([i for i in accurate if i in binary]), **(spread(right) or {})},
        "passed": {
            "of": len(binary),
            "answer_key": sum(str(items[i]["label"]).upper() == "PASS" for i in binary),
            **(spread(passed) or {}),
        },
        "tokens_in": tok_in,
        "tokens_out": tok_out,
        "tokens_reasoning": sum(r.get("reasoning_tokens") or 0 for r in rows),
        "cost_usd": cost,
        "cost_per_1000": cost / len(rows) * 1000 if cost is not None else None,
        "latency_median_s": st.median(latency) if latency else None,
        "latency_p90_s": latency[int(0.9 * (len(latency) - 1))] if latency else None,
        "per_item": per_item,
    }


def agreement(summaries: dict[str, dict], items: dict[str, dict]) -> dict:
    """On how many items did every judge give the same most common mark?"""
    out = {}
    for kind in sorted({it["kind"] for it in items.values()}):
        ids = [i for i, it in items.items() if it["kind"] == kind]
        same = [i for i in ids if len({s["per_item"][i]["most_common"] for s in summaries.values()}) == 1]
        out[kind] = {"items": len(ids), "all_agree": len(same)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default="items_v2.jsonl")
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--dry-run", action="store_true", help="read the dry-run results folder")
    args = ap.parse_args()

    items = load_items(args.items)
    runs = load_runs(args.items, args.repeats, args.dry_run)
    summaries = {name: summarise(rows, items) for name, rows in runs.items()}
    out_dir = results_dir(args.items, args.dry_run)
    unsupported = {
        p.name.removesuffix(".unsupported.json"): json.loads(p.read_text(encoding="utf-8"))
        for p in out_dir.glob("*.unsupported.json")
    }
    agree = agreement(summaries, items) if summaries else {}
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "items": args.items,
                "repeats": args.repeats,
                "prices_checked": PRICES_CHECKED,
                "agreement_between_judges": agree,
                "unsupported": unsupported,
                "runs": summaries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for name, s in summaries.items():
        print(
            f"\n== {name} ({s['model']}): {s['calls']} calls, {s['complete_runs']} complete runs, "
            f"{s['unparsed']} unreadable, {s['cut_off']} cut off"
        )
        for group, c in s["consistency"].items():
            print(
                f"   {group:<15} same mark every run: {c['same_every_run']:>2} of {c['items']:<2}"
                f"   chance two runs disagree: {c['pairwise_disagree']:.1%}"
            )
        r, p = s["right_on_clear_pass_fail"], s["passed"]
        if r.get("mean") is not None:
            print(f"   right on clear pass/fail items: {r['mean']:.1f} of {r['of']} (runs {r['min']}-{r['max']})")
        if p.get("mean") is not None:
            print(
                f"   answers passed: {p['mean']:.1f} of {p['of']} (runs {p['min']}-{p['max']}); "
                f"answer key says {p['answer_key']}"
            )
        if s["cost_usd"] is not None:
            print(
                f"   cost ${s['cost_usd']:.4f} (${s['cost_per_1000']:.3f} per 1,000 marks); "
                f"median {s['latency_median_s']}s, p90 {s['latency_p90_s']}s per call"
            )
    for kind, a in agree.items():
        print(f"\nAll judges agreed on {a['all_agree']} of {a['items']} {kind} items.")
    for name, u in unsupported.items():
        print(f"{name}: {u['model']} refused temperature 0.")
    print(f"\nPrices are list prices checked {PRICES_CHECKED}.")


if __name__ == "__main__":
    main()
