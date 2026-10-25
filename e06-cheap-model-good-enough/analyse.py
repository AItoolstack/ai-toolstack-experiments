"""E06: score every saved answer against the written answer key, then compare models.

Scoring is plain code, no LLM judge. Three kinds of output:
  1. accuracy per model and task, cost per 1,000 calls, median latency
  2. accuracy per trap (the failure types written down in build_items.py before any run)
  3. two cascades: the cheap model's answer is kept unless a cheap check fails, then a larger
     model's answer (already run on the same item and repeat) is used instead. No extra calls.

    python analyse.py                      # items.jsonl, real results
    python analyse.py --items items_samples.jsonl --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone

from build_items import INVOICE_FIELDS, TOOLS
from common import HERE, MODELS, cost_usd, load_items, load_runs

TOOL_NOW = datetime(2026, 11, 4, 10, 15, tzinfo=timezone.utc)
TOOL_SPECS = {t["name"]: t["parameters"] for t in TOOLS}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


# --------------------------------------------------------------------------- parsing helpers
def parse_json(text: str) -> dict | None:
    try:
        obj = json.loads(text[text.index("{") : text.rindex("}") + 1])
        return obj if isinstance(obj, dict) else None
    except (ValueError, json.JSONDecodeError):
        return None


def as_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace("£", "").replace("$", "").replace("€", "").strip())
        except ValueError:
            return None
    return None


def as_instant(v) -> datetime | None:
    if not isinstance(v, str) or not ISO_DT.match(v):
        return None
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # UK is on UTC+00:00 in November


def norm_text(s: str) -> str:
    s = re.sub(r"[^\w\s&-]", " ", s.lower()).replace("limited", "ltd")
    return " ".join(s.split())


# --------------------------------------------------------------------------- matching
def matches(gold, pred) -> bool:
    """One value against the answer key. See build_items.py for the gold conventions."""
    if isinstance(gold, dict):
        if "any_of" in gold:
            return any(matches(g, pred) for g in gold["any_of"])
        if "set" in gold:
            return isinstance(pred, list) and {str(p).strip().lower() for p in pred} == {g.lower() for g in gold["set"]}
        if "present" in gold:
            return isinstance(pred, str) and bool(pred.strip())
    if gold is None:
        return pred is None or pred == ""
    if isinstance(gold, bool):
        return pred is gold or str(pred).lower() == str(gold).lower()
    if isinstance(gold, (int, float)):
        n = as_number(pred)
        return n is not None and abs(n - gold) < 0.005
    if isinstance(gold, str):
        if ISO_DT.match(gold):
            a, b = as_instant(gold), as_instant(pred)
            return a is not None and a == b
        if ISO_DATE.match(gold):
            return pred == gold
        return isinstance(pred, str) and norm_text(pred) == norm_text(gold)
    return False


def tool_call_of(row: dict) -> tuple[str | None, dict | None, str]:
    """(name, args, how) for the answer. `how` flags shapes a real system would mishandle."""
    calls = row.get("tool_calls") or []
    if len(calls) > 1:
        return calls[0]["name"], None, "several_calls"
    if calls:
        try:
            args = json.loads(calls[0]["arguments"] or "{}")
        except json.JSONDecodeError:
            return calls[0]["name"], None, "bad_arguments_json"
        return calls[0]["name"], args, "ok"
    if parse_json(row.get("content", "")) and re.search(r'"(name|function|tool)"', row.get("content", "")):
        return None, None, "call_written_as_text"
    return None, None, "no_call"


def score(item: dict, row: dict) -> dict:
    """{'correct': bool, 'errors': [str]} for one answer."""
    gold, errors = item["gold"], []
    if item["task"] == "invoice":
        pred = parse_json(row.get("content", ""))
        if pred is None:
            return {"correct": False, "errors": ["unparsed"]}
        errors = [f for f in INVOICE_FIELDS if not matches(gold[f], pred.get(f))]
    elif item["task"] == "tool":
        name, args, how = tool_call_of(row)
        if how not in ("ok", "no_call"):
            errors.append(how)
        elif gold["call"] is None:
            if name is not None:
                errors.append("called_when_should_ask")
        elif name is None:
            errors.append("no_call_when_should_call")
        elif name != gold["call"]:
            errors.append("wrong_tool")
        else:
            errors += [f"arg:{k}" for k, g in gold["args"].items() if not matches(g, (args or {}).get(k))]
    else:
        pred = parse_json(row.get("content", ""))
        if pred is None:
            errors.append("unparsed")
        elif not matches(gold["amount"], pred.get("amount")):
            errors.append("wrong_amount")
    if row.get("finish_reason") == "length":
        errors.append("cut_off")
    return {"correct": not errors, "errors": errors}


# --------------------------------------------------------------------------- cheap checks
def passes_check(item: dict, row: dict) -> bool:
    """A check you could run in production without knowing the answer."""
    if item["task"] == "invoice":
        p = parse_json(row.get("content", ""))
        if p is None or set(INVOICE_FIELDS) - set(p):
            return False
        for f in ("invoice_date", "due_date"):
            if p[f] is not None and (not isinstance(p[f], str) or not ISO_DATE.match(p[f])):
                return False
        try:
            if p["due_date"] and date.fromisoformat(p["due_date"]) < date.fromisoformat(p["invoice_date"]):
                return False
        except (TypeError, ValueError):
            return False
        if not (isinstance(p["currency"], str) and re.fullmatch(r"[A-Z]{3}", p["currency"])):
            return False
        net, tax, gross = (as_number(p[k]) for k in ("net_total", "tax_total", "gross_total"))
        if gross is None or (net is not None and abs(net + (tax or 0) - gross) > 0.011):
            return False
        if bool(p["is_credit_note"]) != (gross < 0):
            return False
        return as_number(p["amount_due"]) is not None
    if item["task"] == "tool":
        name, args, how = tool_call_of(row)
        if how == "no_call":
            return True  # a question can't be checked by code
        if how != "ok" or name not in TOOL_SPECS:
            return False
        spec = TOOL_SPECS[name]
        if any(r not in args for r in spec["required"]):
            return False
        for k, v in args.items():
            prop = spec["properties"].get(k)
            if prop is None or ("enum" in prop and v not in prop["enum"]):
                return False
            if k in ("start", "end"):
                t = as_instant(v)
                if t is None or t < TOOL_NOW:
                    return False
        return True
    p = parse_json(row.get("content", ""))
    n = as_number(p.get("amount")) if p else None
    return n is not None and n >= 0


def answer_key(item: dict, row: dict) -> str:
    """The answer reduced to what matters, so two runs can be compared without knowing the right answer."""
    if item["task"] == "tool":
        name, args, how = tool_call_of(row)
        return json.dumps([name, args, how], sort_keys=True)
    p = parse_json(row.get("content", "")) or {}
    if item["task"] == "rules":
        return str(as_number(p.get("amount")))
    vals = []
    for f in INVOICE_FIELDS:
        v = p.get(f)
        n = as_number(v)
        vals.append(round(n, 2) if n is not None else (norm_text(v) if isinstance(v, str) else v))
    return json.dumps(vals)


# --------------------------------------------------------------------------- analysis
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="items.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fallback", default="sol", help="model used when the cheap check fails")
    args = ap.parse_args()

    items = load_items(args.items)
    runs = load_runs(args.items, args.dry_run)
    order = [m for m in MODELS if m in runs]
    scored = {m: {(r["item"], r["repeat"]): (r, score(items[r["item"]], r)) for r in runs[m]} for m in order}

    summary = {"models": {}, "traps": {}, "cascades": {}}
    print(f"\n{'model':10} {'task':8} {'acc':>6} {'n':>4}  {'$/1k calls':>10}  {'median s':>8}")
    for m in order:
        rows = list(scored[m].values())
        by_task = defaultdict(list)
        for r, s in rows:
            by_task[r["task"]].append((r, s))
        summary["models"][m] = {}
        for task, rs in sorted(by_task.items()) + [("all", rows)]:
            acc = sum(s["correct"] for _, s in rs) / len(rs)
            cost = sum(cost_usd(m, r["prompt_tokens"] or 0, r["completion_tokens"] or 0) for r, _ in rs)
            lat = statistics.median(r["latency_s"] for r, _ in rs)
            summary["models"][m][task] = {
                "accuracy": acc,
                "n": len(rs),
                "usd_per_1k": 1000 * cost / len(rs),
                "median_latency_s": lat,
            }
            print(f"{m:10} {task:8} {acc:6.1%} {len(rs):4}  {1000 * cost / len(rs):10.3f}  {lat:8.2f}")

    traps = sorted({t for it in items.values() for t in it["traps"]})
    print("\nAccuracy by trap (items built to test it):")
    print(f"{'trap':24}" + "".join(f"{m:>10}" for m in order))
    for t in traps:
        ids = {i for i, it in items.items() if t in it["traps"]}
        line, summary["traps"][t] = f"{t:24}", {}
        for m in order:
            rs = [s for (i, _), (_, s) in scored[m].items() if i in ids]
            acc = sum(s["correct"] for s in rs) / len(rs) if rs else float("nan")
            summary["traps"][t][m] = acc
            line += f"{acc:10.0%}"
        print(line)

    fb = args.fallback
    if fb in scored:
        print(f"\nCascades into {fb} (no extra calls; uses {fb}'s answer on the same item and repeat):")
        for m in order:
            if m == fb:
                continue
            res = {}
            # A: escalate when the cheap check fails.
            n = esc = right = 0
            cost = 0.0
            for key, (r, s) in scored[m].items():
                if key not in scored[fb]:
                    continue
                n += 1
                cost += cost_usd(m, r["prompt_tokens"] or 0, r["completion_tokens"] or 0)
                if passes_check(items[key[0]], r):
                    right += s["correct"]
                else:
                    esc += 1
                    fr, fs = scored[fb][key]
                    right += fs["correct"]
                    cost += cost_usd(fb, fr["prompt_tokens"] or 0, fr["completion_tokens"] or 0)
            if n:
                res["check"] = {"accuracy": right / n, "escalated": esc / n, "usd_per_1k": 1000 * cost / n}
            # B: run the cheap model on every repeat; escalate when its answers disagree.
            per_item = defaultdict(list)
            for (i, rep), (r, s) in scored[m].items():
                per_item[i].append((rep, r, s))
            n = esc = right = 0
            cost = 0.0
            for i, rs in per_item.items():
                if (i, 0) not in scored[fb]:
                    continue
                n += 1
                cost += sum(cost_usd(m, r["prompt_tokens"] or 0, r["completion_tokens"] or 0) for _, r, _ in rs)
                if len({answer_key(items[i], r) for _, r, _ in rs}) == 1:
                    right += sorted(rs, key=lambda x: x[0])[0][2]["correct"]
                else:
                    esc += 1
                    fr, fs = scored[fb][(i, 0)]
                    right += fs["correct"]
                    cost += cost_usd(fb, fr["prompt_tokens"] or 0, fr["completion_tokens"] or 0)
            if n:
                res["agreement"] = {"accuracy": right / n, "escalated": esc / n, "usd_per_1k_items": 1000 * cost / n}
            summary["cascades"][m] = res
            for k, v in res.items():
                print(f"  {m:10} {k:9} acc {v['accuracy']:6.1%}  escalated {v['escalated']:5.1%}")

    out = HERE / ("summary-dry.json" if args.dry_run else "summary.json")
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out.name}")


if __name__ == "__main__":
    main()
