"""E06 post-hoc analysis, added 31 Oct 2026 AFTER the frozen results were read.

Nothing here was pre-registered. It reuses the frozen scorer and frozen check (analyse.py)
unchanged, makes no API calls and changes no item, key or result. Every number it prints is
exploratory and must be labelled that way wherever it is quoted.

  1. Latency: per model alone, and end to end for both cascades (the agreement cascade is
     timed two ways: three cheap calls in parallel, or one after another).
  2. One extra check, "no tool call and no question", designed after reading the wrong answers
     that the frozen check accepted. Reported separately from the frozen check.
  3. Cost at volume: the frozen per-1,000-item costs scaled to 100,000 and 1,000,000 items.
  4. Where the cheap models' wrong answers fall, by task and error type.

    python analyse_posthoc.py              # held-out cohort (the 81 new items)
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict

from analyse import answer_key, passes_check, score, tool_call_of
from common import HERE, PRICES, cost_usd, load_items, read_jsonl

RUN = HERE / "results_frozen_20261029"
CHEAP = ("oss-20b", "luna", "glm-flash", "oss-120b")
FALLBACK = "sol"


def claims_action(item: dict, row: dict) -> bool:
    """Escalate a tool reply that makes no native call and asks no question.

    The assistant's prompt allows three moves: call a tool, ask one question, or say no tool
    fits. A reply with no call and no question is either a decline or, as in the wrong answers
    read on 31 Oct, a claim or promise of an action that never happened ("I've created a
    ticket"). The rule can't tell those apart, so declines are counted as false alarms.
    """
    if item["task"] != "tool":
        return False
    _, _, how = tool_call_of(row)
    return how == "no_call" and "?" not in (row.get("content") or "")


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def main() -> None:
    items = load_items("items.jsonl")
    samples = set(load_items("items_samples.jsonl"))
    held = {i: it for i, it in items.items() if i not in samples}
    rows = {m: {(r["item"], r["repeat"]): r for r in read_jsonl(RUN / f"{m}.jsonl") if r["item"] in held}
            for m in (*CHEAP, FALLBACK)}
    out = {"cohort": "heldout", "items": len(held), "posthoc": True, "added": "2026-10-31"}

    # 1. latency ------------------------------------------------------------------------------
    print(f"Held-out items: {len(held)}\n\n1. Latency in seconds, median / 90th percentile (post-hoc)")
    lat = {}
    for m in (*CHEAP, FALLBACK):
        xs = [r["latency_s"] for r in rows[m].values()]
        lat[m] = {"median": statistics.median(xs), "p90": pct(xs, 0.9)}
        print(f"  {m:10} alone            {lat[m]['median']:6.2f} / {lat[m]['p90']:6.2f}")
    out["latency_alone"] = lat
    out["latency_cascades"] = {}
    for m in CHEAP:
        par, seq, chk = [], [], []
        for i in held:
            reps = [rows[m][(i, k)] for k in range(3)]
            fb = rows[FALLBACK][(i, 0)]["latency_s"]
            esc = len({answer_key(held[i], r) for r in reps}) > 1
            par.append(max(r["latency_s"] for r in reps) + (fb if esc else 0))
            seq.append(sum(r["latency_s"] for r in reps) + (fb if esc else 0))
            for r in reps:
                chk.append(r["latency_s"] + (0 if passes_check(held[i], r) else fb))
        res = {"agreement_parallel": (statistics.median(par), pct(par, 0.9)),
               "agreement_sequential": (statistics.median(seq), pct(seq, 0.9)),
               "check": (statistics.median(chk), pct(chk, 0.9))}
        out["latency_cascades"][m] = res
        for k, (a, b) in res.items():
            print(f"  {m:10} {k:22} {a:6.2f} / {b:6.2f}")

    # 2. the extra check -----------------------------------------------------------------------
    print("\n2. Extra check designed after the results: 'no tool call and no question'")
    out["action_claim_check"] = {}
    for m in CHEAP:
        n = wrong = frozen_caught = extra_caught = extra_false = 0
        right_after = cost = 0.0
        examples = []
        for (i, rep), r in rows[m].items():
            it, s = held[i], score(held[i], r)
            n += 1
            ok_frozen = passes_check(it, r)
            claim = claims_action(it, r)
            cost += cost_usd(m, r["prompt_tokens"] or 0, r["completion_tokens"] or 0)
            if not s["correct"]:
                wrong += 1
                frozen_caught += not ok_frozen
                extra_caught += ok_frozen and claim
                if ok_frozen and claim:
                    examples.append(f"{i} r{rep}")
            elif claim:
                extra_false += 1
            escalate = (not ok_frozen) or claim
            if escalate:
                fr = rows[FALLBACK][(i, 0)]
                right_after += score(it, fr)["correct"]
                cost += cost_usd(FALLBACK, fr["prompt_tokens"] or 0, fr["completion_tokens"] or 0)
            else:
                right_after += s["correct"]
        out["action_claim_check"][m] = {
            "responses": n, "wrong": wrong, "caught_by_frozen_check": frozen_caught,
            "extra_caught": extra_caught, "extra_false_alarms": extra_false,
            "cascade_correct": right_after, "cascade_usd_per_1k": 1000 * cost / n, "examples": examples}
        print(f"  {m:10} wrong {wrong:3}  frozen check caught {frozen_caught}  extra check caught {extra_caught}"
              f"  false alarms {extra_false}  cascade {int(right_after)}/{n}  ${1000 * cost / n:.4f}/1k  {examples}")

    # 3. cost at volume ------------------------------------------------------------------------
    summary = json.loads((HERE / "analysis_frozen_20261029_heldout" / "summary-v2.json").read_text(encoding="utf-8"))
    print("\n3. Cost at volume, USD (frozen list prices; held-out per-1,000 figures scaled)")
    vol = {}
    sol_1k = summary["models"][FALLBACK]["all"]["usd_per_1k"]
    for name, per1k in [("sol alone", sol_1k)] + [
        (f"{m} + agreement", summary["cascades"][m]["all"]["agreement"]["usd_per_1k_items"]) for m in CHEAP
    ]:
        if per1k is None:
            continue
        vol[name] = {"per_1k": per1k, "per_100k": per1k * 100, "per_1m": per1k * 1000}
        print(f"  {name:22} 1k ${per1k:8.4f}   100k ${per1k * 100:8.2f}   1M ${per1k * 1000:9.2f}")
    out["cost_at_volume"] = vol

    # 4. where the errors are -------------------------------------------------------------------
    print("\n4. Wrong cheap answers by task and error type")
    by = defaultdict(Counter)
    for m in CHEAP:
        for (i, _), r in rows[m].items():
            s = score(held[i], r)
            if not s["correct"]:
                for e in s["errors"]:
                    by[held[i]["task"]][re.sub(r"^arg:.*", "wrong_argument", e)] += 1
    out["errors_by_task"] = {t: dict(c) for t, c in by.items()}
    for t, c in by.items():
        print(f"  {t:8} {sum(c.values()):3}  {dict(c.most_common())}")

    (HERE / "analysis_frozen_20261029_heldout" / "posthoc-2026-10-31.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("\nWrote analysis_frozen_20261029_heldout/posthoc-2026-10-31.json")


if __name__ == "__main__":
    main()
