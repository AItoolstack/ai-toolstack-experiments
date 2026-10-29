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
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from build_items import INVOICE_FIELDS, TOOLS
from common import CONTROL_MODELS, HERE, MODEL_REPEATS, MODELS, REPEATS, cost_usd, load_items, load_runs, results_dir

ANALYSIS_VERSION = "v4"

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
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    if isinstance(v, str):
        try:
            n = float(v.replace("£", "").replace("$", "").replace("€", "").strip())
            return n if math.isfinite(n) else None
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
        except (json.JSONDecodeError, TypeError):
            return calls[0]["name"], None, "bad_arguments_json"
        if not isinstance(args, dict):
            return calls[0]["name"], None, "bad_arguments_shape"
        return calls[0]["name"], args, "ok"
    if parse_json(row.get("content", "")) is not None and re.search(r'"(name|function|tool)"', row.get("content", "")):
        return None, None, "call_written_as_text"
    return None, None, "no_call"


def score(item: dict, row: dict) -> dict:
    """{'correct': bool, 'errors': [str]} for one answer."""
    gold, errors = item["gold"], []
    if item["task"] == "invoice":
        pred = parse_json(row.get("content", ""))
        if pred is None:
            errors.append("unparsed")
        else:
            errors = [f"missing:{f}" for f in INVOICE_FIELDS if f not in pred]
            errors += [f for f in INVOICE_FIELDS if f in pred and not matches(gold[f], pred[f])]
    elif item["task"] == "tool":
        name, args, how = tool_call_of(row)
        if how not in ("ok", "no_call"):
            errors.append(how)
        elif name is not None and (name not in TOOL_SPECS or not schema_valid(args, TOOL_SPECS[name])):
            errors.append("invalid_tool_schema")
        elif gold["call"] is None:
            if name is not None:
                errors.append("called_when_should_ask")
            elif not row.get("content", "").strip():
                errors.append("empty_answer")
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
        elif as_number(pred.get("amount")) is None:
            errors.append("unreadable_amount")
        elif not matches(gold["amount"], pred.get("amount")):
            errors.append("wrong_amount")
    if row.get("finish_reason") == "length":
        errors.append("cut_off")
    elif row.get("finish_reason") in ("content_filter", "incomplete"):
        errors.append("incomplete_response")
    return {"correct": not errors, "errors": errors}


# --------------------------------------------------------------------------- cheap checks
def baseline_check(item: dict, row: dict) -> bool:
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


def schema_valid(value, schema: dict) -> bool:
    """The JSON Schema subset used by the nine tools; no answer-key access."""
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict) or set(schema.get("required", [])) - set(value):
            return False
        props = schema.get("properties", {})
        return all(k in props and schema_valid(v, props[k]) for k, v in value.items())
    if kind == "array":
        return isinstance(value, list) and all(schema_valid(v, schema.get("items", {})) for v in value)
    if kind == "string" and not isinstance(value, str):
        return False
    if kind == "number" and (
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
    ):
        return False
    if kind == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
        return False
    if kind == "boolean" and not isinstance(value, bool):
        return False
    return "enum" not in schema or value in schema["enum"]


def passes_check(item: dict, row: dict, version: str = "v2") -> bool:
    if version == "baseline":
        return baseline_check(item, row)
    if row.get("finish_reason") in ("length", "content_filter", "incomplete"):
        return False
    if not baseline_check(item, row):
        return False
    if item["task"] == "invoice":
        p = parse_json(row.get("content", ""))
        if set(p) != set(INVOICE_FIELDS) or not isinstance(p["is_credit_note"], bool):
            return False
        for field in ("invoice_date", "due_date"):
            if p[field] is not None:
                try:
                    date.fromisoformat(p[field])
                except (ValueError, TypeError):
                    return False
        for field in ("supplier_name", "invoice_number"):
            if p[field] is not None and not isinstance(p[field], str):
                return False
        return all(
            p[k] is None or (isinstance(p[k], (int, float)) and not isinstance(p[k], bool) and math.isfinite(p[k]))
            for k in ("net_total", "tax_total", "gross_total", "amount_due")
        )
    if item["task"] == "tool":
        name, args, how = tool_call_of(row)
        if how == "no_call":
            return bool(row.get("content", "").strip())
        if not schema_valid(args, TOOL_SPECS[name]):
            return False
        if "start" in args and "end" in args:
            return as_instant(args["end"]) > as_instant(args["start"])
    return True


def check_metrics(pairs: list, check) -> dict:
    counts = {"correct_accepted": 0, "correct_escalated": 0, "wrong_caught": 0, "wrong_accepted": 0}
    for row, scored in pairs:
        accepted = check(row)
        label = (
            ("correct_accepted" if accepted else "correct_escalated")
            if scored["correct"]
            else ("wrong_accepted" if accepted else "wrong_caught")
        )
        counts[label] += 1
    n = len(pairs)
    accepted = counts["correct_accepted"] + counts["wrong_accepted"]
    wrong = counts["wrong_caught"] + counts["wrong_accepted"]
    return {
        **counts,
        "n": n,
        "accepted_accuracy": counts["correct_accepted"] / accepted if accepted else None,
        "error_catch_rate": counts["wrong_caught"] / wrong if wrong else None,
        "escalation_rate": (n - accepted) / n if n else None,
    }


def cascade(items, cheap, fallback, task, repeats, mode, check_version, fallback_repeats=None):
    """Only compare complete cohorts; never silently intersect incomplete runs."""
    ids = {i for i, item in items.items() if task == "all" or item["task"] == task}
    required_repeats = 3 if mode == "agreement" else repeats
    required = {(i, r) for i in ids for r in range(required_repeats)}
    single_fallback = mode == "agreement" or fallback_repeats == 1
    fallback_required = {(i, 0) for i in ids} if single_fallback else required
    missing_cheap, missing_fallback = required - cheap.keys(), fallback_required - fallback.keys()
    if missing_cheap or missing_fallback:
        return {
            "status": "incomplete",
            "required_repeats": required_repeats,
            "missing_cheap": len(missing_cheap),
            "missing_fallback": len(missing_fallback),
        }
    right = escalated = 0
    cost = fallback_cost = 0.0
    latencies = []
    keys = [(i, 0) for i in sorted(ids)] if mode == "agreement" else sorted(required)
    for key in keys:
        rs = [cheap[(key[0], rep)] for rep in range(3)] if mode == "agreement" else [cheap[key]]
        accepted = (
            len({answer_key(items[key[0]], r) for r, _ in rs}) == 1
            if mode == "agreement"
            else passes_check(items[key[0]], rs[0][0], check_version)
        )
        fallback_key = (key[0], 0) if single_fallback else key
        fr, fs = fallback[fallback_key]
        chosen = rs[0][1] if accepted else fs
        right += chosen["correct"]
        escalated += not accepted
        cost += sum(cost_usd(r["model"], r["prompt_tokens"] or 0, r["completion_tokens"] or 0) for r, _ in rs)
        fc = cost_usd(fr["model"], fr["prompt_tokens"] or 0, fr["completion_tokens"] or 0)
        fallback_cost += fc
        if not accepted:
            cost += fc
        # Sequential policy estimate, not measured end-to-end cascade latency.
        latencies.append(sum(r["latency_s"] for r, _ in rs) + (0 if accepted else fr["latency_s"]))
    n = len(keys)
    return {
        "status": "complete",
        "n": n,
        "n_items": len(ids),
        "fallback_repeat_policy": "reuse_repeat_0" if single_fallback else "matched_repeat",
        "accuracy": right / n,
        "escalated": escalated / n,
        "usd_per_1k_items": 1000 * cost / n,
        "fallback_usd_per_1k_items": 1000 * fallback_cost / n,
        "fallback_accuracy": sum(fallback[(k[0], 0) if single_fallback else k][1]["correct"] for k in keys) / n,
        "estimated_sequential_median_latency_s": statistics.median(latencies),
    }


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
    ap.add_argument("--run-tag", default="")
    ap.add_argument("--repeats", type=int, help="override per-model expected repeats; use 1 for the pilot")
    ap.add_argument("--checks", choices=("baseline", "v2"), default="v2")
    ap.add_argument("--cohort", choices=("all", "heldout", "development"), default="all")
    args = ap.parse_args()
    if args.repeats is not None and not 1 <= args.repeats <= REPEATS:
        ap.error(f"repeats must be between 1 and {REPEATS}")

    items = load_items(args.items)
    manifest = None
    if args.cohort != "all":
        manifest_path = HERE / "dataset-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["items_sha256"] != hashlib.sha256((HERE / args.items).read_bytes()).hexdigest():
            ap.error("dataset manifest does not match --items; do not apply cohort IDs to a different dataset")
        selected_ids = set(manifest["held_out_ids" if args.cohort == "heldout" else "development_ids"])
        items = {key: item for key, item in items.items() if key in selected_ids}
        if not items:
            ap.error("the selected cohort has no items")
    expected_repeats = {m: args.repeats if args.repeats is not None else MODEL_REPEATS[m] for m in MODELS}
    runs = load_runs(args.items, args.dry_run, args.run_tag)
    runs = {
        m: [r for r in rows if r["repeat"] < expected_repeats[m] and r["item"] in items] for m, rows in runs.items()
    }
    runs = {m: rows for m, rows in runs.items() if rows}
    order = [m for m in MODELS if m in runs]
    scored = {m: {(r["item"], r["repeat"]): (r, score(items[r["item"]], r)) for r in runs[m]} for m in order}
    for m in order:
        if len(scored[m]) != len(runs[m]):
            ap.error(f"duplicate item/repeat rows for {m}")
        configs = {r.get("config_sha256", "legacy") for r in runs[m]}
        if len(configs) > 1:
            ap.error(f"mixed run configurations for {m}")

    summary = {
        "analysis_version": ANALYSIS_VERSION,
        "checks": args.checks,
        "items_file": args.items,
        "run_tag": args.run_tag,
        "cohort": args.cohort,
        "selected_item_ids": sorted(items),
        "expected_repeats": args.repeats if args.repeats is not None else REPEATS,
        "expected_repeats_by_model": {m: expected_repeats[m] for m in order},
        "models": {},
        "traps": {},
        "cascades": {},
        "coverage": {},
        "checks_by_version": {},
        "kinds": {},
        "cost_basis": "Listed token prices in common.py; successful answers only. Failed attempts and "
        "cache discounts are not priced. Legacy latency omits retries.",
    }
    summary["provenance"] = {
        "items_sha256": hashlib.sha256((HERE / args.items).read_bytes()).hexdigest(),
        "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "result_sha256": {
            m: hashlib.sha256(
                (results_dir(args.items, args.dry_run, args.run_tag) / f"{m}.jsonl").read_bytes()
            ).hexdigest()
            for m in order
        },
    }
    if manifest is not None:
        summary["provenance"]["dataset_manifest_sha256"] = hashlib.sha256(
            (HERE / "dataset-manifest.json").read_bytes()
        ).hexdigest()
    print(f"\n{'model':10} {'task':8} {'acc':>6} {'n':>4}  {'$/1k calls':>10}  {'median s':>8}")
    for m in order:
        rows = list(scored[m].values())
        by_task = defaultdict(list)
        for r, s in rows:
            by_task[r["task"]].append((r, s))
        summary["models"][m] = {}
        required = {(i, r) for i in items for r in range(expected_repeats[m])}
        summary["coverage"][m] = {
            "saved": len(rows),
            "expected": len(required),
            "complete": required <= scored[m].keys(),
            "missing": [list(k) for k in sorted(required - scored[m].keys())],
        }
        if not summary["coverage"][m]["complete"]:
            print(f"WARNING: {m} incomplete: {len(rows)}/{len(required)}; observed accuracy only")
        summary["checks_by_version"][m] = {"baseline": {}, "v2": {}}
        for task, rs in sorted(by_task.items()) + [("all", rows)]:
            acc = sum(s["correct"] for _, s in rs) / len(rs)
            cost = sum(cost_usd(m, r["prompt_tokens"] or 0, r["completion_tokens"] or 0) for r, _ in rs)
            lat = statistics.median(r["latency_s"] for r, _ in rs)
            summary["models"][m][task] = {
                "accuracy": acc,
                "n": len(rs),
                "n_items": len({r["item"] for r, _ in rs}),
                "usd_per_1k": 1000 * cost / len(rs),
                "median_latency_s": lat,
                "errors": dict(Counter(e for _, s in rs for e in s["errors"])),
            }
            for version in ("baseline", "v2"):
                metrics = check_metrics(rs, lambda r, version=version: passes_check(items[r["item"]], r, version))
                summary["checks_by_version"][m][version][task] = metrics
            print(f"{m:10} {task:8} {acc:6.1%} {len(rs):4}  {1000 * cost / len(rs):10.3f}  {lat:8.2f}")

    traps = sorted({t for it in items.values() for t in it["traps"]})
    summary["trap_counts"] = {}
    print("\nCorrect calls by trap (repeats are correlated; item counts are saved separately):")
    print(f"{'trap':24}" + "".join(f"{m:>10}" for m in order))
    for t in traps:
        ids = {i for i, it in items.items() if t in it["traps"]}
        summary["trap_counts"][t] = {
            m: {
                "n_calls": sum(i in ids for i, _ in scored[m]),
                "n_items": len({i for i, _ in scored[m] if i in ids}),
                "correct_calls": sum(s["correct"] for (i, _), (_, s) in scored[m].items() if i in ids),
            }
            for m in order
        }
        line, summary["traps"][t] = f"{t:24}", {}
        for m in order:
            rs = [s for (i, _), (_, s) in scored[m].items() if i in ids]
            acc = sum(s["correct"] for s in rs) / len(rs) if rs else None
            summary["traps"][t][m] = acc
            count = f"{sum(s['correct'] for s in rs)}/{len(rs)}"
            line += f"{count:>10}" if rs else f"{'n/a':>10}"
        print(line)

    for kind in sorted({item["kind"] for item in items.values()}):
        ids = {i for i, item in items.items() if item["kind"] == kind}
        summary["kinds"][kind] = {
            m: {
                "n_calls": sum(i in ids for i, _ in scored[m]),
                "n_items": len({i for i, _ in scored[m] if i in ids}),
                "correct_calls": sum(s["correct"] for (i, _), (_, s) in scored[m].items() if i in ids),
            }
            for m in order
        }

    fb = args.fallback
    for m in order:
        if m == fb or m in CONTROL_MODELS:
            continue
        summary["cascades"][m] = {}
        for task in sorted({i["task"] for i in items.values()}) + ["all"]:
            summary["cascades"][m][task] = {}
            for mode in ("check", "agreement"):
                result = cascade(
                    items,
                    scored[m],
                    scored.get(fb, {}),
                    task,
                    expected_repeats[m],
                    mode,
                    args.checks,
                    expected_repeats.get(fb, REPEATS),
                )
                summary["cascades"][m][task][mode] = result
                if result["status"] == "complete":
                    print(f"Cascade {m} -> {fb}, {task}, {mode}: {result['accuracy']:.1%}, n={result['n']}")
                else:
                    print(f"Cascade {m} -> {fb}, {task}, {mode}: incomplete; no estimate")

    out_dir = HERE / results_dir(args.items, args.dry_run, args.run_tag).name.replace("results", "analysis", 1)
    if args.cohort != "all":
        out_dir = out_dir.with_name(out_dir.name + "_" + args.cohort)
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"summary-{args.checks}.json"
    out.write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    with (out_dir / "row-audit.jsonl").open("w", encoding="utf-8") as f:
        for model in order:
            source = results_dir(args.items, args.dry_run, args.run_tag) / f"{model}.jsonl"
            for line, row in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
                if not row.strip():
                    continue
                r = json.loads(row)
                if r["repeat"] >= expected_repeats[model] or r["item"] not in items:
                    continue
                item = items[r["item"]]
                s = score(item, r)
                flags = [
                    e
                    for e in s["errors"]
                    if e
                    in {
                        "unparsed",
                        "unreadable_amount",
                        "bad_arguments_json",
                        "bad_arguments_shape",
                        "call_written_as_text",
                        "several_calls",
                        "cut_off",
                        "incomplete_response",
                    }
                ]
                if item["task"] == "tool" and not r.get("tool_calls") and not r.get("content", "").strip():
                    flags.append("empty_answer")
                if (
                    item["task"] == "tool"
                    and not r.get("tool_calls")
                    and any(t in r.get("content", "") for t in TOOL_SPECS)
                    and "call_written_as_text" not in flags
                ):
                    flags.append("possible_call_text_review")
                audit = {
                    "file": source.name,
                    "line": line,
                    "model": model,
                    "item": r["item"],
                    "repeat": r["repeat"],
                    "task": r["task"],
                    **s,
                    "flags": flags,
                    "baseline_check_passed": passes_check(item, r, "baseline"),
                    "v2_check_passed": passes_check(item, r, "v2"),
                }
                f.write(json.dumps(audit) + "\n")
                if flags:
                    print(f"Audit {source.name}:{line} {r['item']} repeat {r['repeat']}: {', '.join(flags)}")
    print(f"\nWrote {out.relative_to(HERE)} and row-audit.jsonl")


if __name__ == "__main__":
    main()
