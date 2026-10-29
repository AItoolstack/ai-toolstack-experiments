"""Recheck saved pilot health and project token costs offline. No credentials or API calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter

from analyse import as_number, parse_json, tool_call_of
from common import (
    HERE,
    MODEL_REPEATS,
    MODELS,
    PRICES,
    PRICES_CHECKED,
    STUDY_MODELS,
    cost_usd,
    load_items,
    load_runs,
    load_tools,
    results_dir,
)
from run import MAX_TOKENS, RUNNER_VERSION, request_body

TARGETS = {"invoice": 36, "tool": 36, "rules": 30}
REVIEW_IDS = {
    "invoice": ["inv01", "inv02", "inv03"],
    "tool": ["tl01", "tl02", "tl03"],
    "rules": ["rl01", "rl02", "rl03"],
}


def health_report(items_file="items_samples.jsonl", tag="v2", evaluation=False) -> dict:
    """Describe saved run health without calculating accuracy or consulting answer values."""
    items = load_items(items_file)
    tools = load_tools()
    runs = load_runs(items_file, False, tag)
    report = {
        "review_date": "2026-10-29",
        "items_file": items_file,
        "run_tag": tag,
        "run_kind": "evaluation" if evaluation else "pilot",
        "items_sha256": hashlib.sha256((HERE / items_file).read_bytes()).hexdigest(),
        "prices_checked_in_config": PRICES_CHECKED,
        "price_caveat": "Historical configured list prices; not independently reverified or reconciled to billing.",
        "cost_caveat": "Successful saved calls only; retries, preflights and earlier development spend are additional.",
        "projection_caveat": (
            "Task-weighted extrapolation from seven pilot items per task; new policy lengths may differ."
        ),
        "study_models_without_revised_pilot": sorted(set(STUDY_MODELS) - set(runs)),
        "study_models": list(STUDY_MODELS),
        "models": {},
    }
    for name, rows in runs.items():
        config = {
            "runner_version": RUNNER_VERSION,
            "spec": MODELS[name],
            "max_tokens": MAX_TOKENS,
            "requests": [request_body(MODELS[name], item, tools) for item in items.values()],
            "items_sha256": report["items_sha256"],
        }
        fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        problems = {k: [] for k in ("unparsed", "cut_off", "text_call", "malformed_call", "possible_call_text")}
        for row in rows:
            item, content = items[row["item"]], row.get("content", "")
            parsed = parse_json(content)
            if item["task"] in ("invoice", "rules") and (
                parsed is None or item["task"] == "rules" and as_number(parsed.get("amount")) is None
            ):
                problems["unparsed"].append(row["item"])
            if row.get("finish_reason") in ("length", "incomplete"):
                problems["cut_off"].append(row["item"])
            if item["task"] == "tool":
                how = tool_call_of(row)[2]
                if how == "call_written_as_text":
                    problems["text_call"].append(row["item"])
                elif how not in ("ok", "no_call"):
                    problems["malformed_call"].append(row["item"])
                if not row.get("tool_calls") and any(t["name"] in content for t in tools):
                    problems["possible_call_text"].append(row["item"])
        task_costs = {}
        p_in, p_out = PRICES[name]
        for task, count in TARGETS.items():
            subset = [row for row in rows if row["task"] == task]
            mean_in = sum(row.get("prompt_tokens") or 0 for row in subset) / len(subset)
            mean_out = sum(row.get("completion_tokens") or 0 for row in subset) / len(subset)
            task_costs[task] = {
                "pilot_calls": len(subset),
                "mean_input_tokens": mean_in,
                "mean_output_tokens": mean_out,
                "full_items": count,
                "projected_usd_one_repeat": count * (mean_in * p_in + mean_out * p_out) / 1e6,
                "projected_usd_one_repeat_double_output": count * (mean_in * p_in + 2 * mean_out * p_out) / 1e6,
            }
        repeats = MODEL_REPEATS[name] if evaluation else 1
        expected = {(item, rep) for item in items for rep in range(repeats)}
        observed = [(row["item"], row["repeat"]) for row in rows]
        expected_host = (
            "Z.AI" if name.startswith("glm-") else "Groq" if MODELS[name]["provider"] == "openrouter" else "OpenAI"
        )
        report["models"][name] = {
            "saved_calls": len(rows),
            "coverage_complete": set(observed) == expected and len(observed) == len(expected),
            "recorded_run_dates": sorted({row["ts"].split("T")[0] for row in rows}),
            "timestamp_caveat": "Raw timestamps contain no UTC offset; date preserved as recorded.",
            "source_sha256": hashlib.sha256(
                (results_dir(items_file, False, tag) / f"{name}.jsonl").read_bytes()
            ).hexdigest(),
            "current_request_fingerprint_matches": all(row.get("config_sha256") == fingerprint for row in rows),
            "served_by": dict(Counter(row.get("served_by") for row in rows)),
            "expected_host_matches": all(
                str(row.get("served_by")).casefold() == expected_host.casefold() for row in rows
            ),
            "reasoning_tokens_reported": sum(row.get("reasoning_tokens") is not None for row in rows),
            "reasoning_tokens_positive": sum((row.get("reasoning_tokens") or 0) > 0 for row in rows),
            "usage_complete": all(
                isinstance(row.get(field), int) and row[field] >= 0
                for row in rows
                for field in ("prompt_tokens", "completion_tokens")
            ),
            "max_completion_tokens": max(row.get("completion_tokens") or 0 for row in rows),
            "saved_call_estimated_usd": sum(
                cost_usd(name, row.get("prompt_tokens") or 0, row.get("completion_tokens") or 0) for row in rows
            ),
            "over_configured_cap": sum((row.get("completion_tokens") or 0) > MAX_TOKENS for row in rows),
            "problems": problems,
            "task_cost_projection": task_costs,
            "projected_usd_three_repeats": 3 * sum(c["projected_usd_one_repeat"] for c in task_costs.values()),
            "projected_usd_three_repeats_double_output": 3
            * sum(c["projected_usd_one_repeat_double_output"] for c in task_costs.values()),
            "manual_review_selection": REVIEW_IDS,
        }
    report["hypothetical_usd_saved_models_all_three_repeats"] = sum(
        model["projected_usd_three_repeats"] for model in report["models"].values()
    )
    report["hypothetical_usd_saved_models_all_three_repeats_double_output"] = sum(
        model["projected_usd_three_repeats_double_output"] for model in report["models"].values()
    )
    report["study_projection"] = study_projection(report["models"])
    report["saved_call_estimated_usd"] = sum(m["saved_call_estimated_usd"] for m in report["models"].values())
    return report


def study_projection(models: dict) -> dict:
    """Apply the actual study schedule, retaining missing-model coverage explicitly."""
    included = {name: data for name, data in models.items() if name in STUDY_MODELS}
    estimates = {}
    for name, data in included.items():
        repeats = MODEL_REPEATS[name]
        estimates[name] = {
            "repeats": repeats,
            "calls": repeats * sum(TARGETS.values()),
            "usd": repeats * sum(t["projected_usd_one_repeat"] for t in data["task_cost_projection"].values()),
            "usd_double_output": repeats
            * sum(t["projected_usd_one_repeat_double_output"] for t in data["task_cost_projection"].values()),
        }
    missing = sorted(set(STUDY_MODELS) - set(included))
    return {
        "complete_model_coverage": not missing,
        "missing_models": missing,
        "models": estimates,
        "calls": sum(m["calls"] for m in estimates.values()),
        "usd": sum(m["usd"] for m in estimates.values()),
        "usd_double_output": sum(m["usd_double_output"] for m in estimates.values()),
        "by_provider_usd": {
            provider: sum(m["usd"] for name, m in estimates.items() if MODELS[name]["provider"] == provider)
            for provider in {MODELS[name]["provider"] for name in estimates}
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", default="items_samples.jsonl")
    parser.add_argument("--run-tag", default="v2")
    parser.add_argument("--evaluation", action="store_true", help="expect each model's full-run repeat schedule")
    args = parser.parse_args()
    run_folder = results_dir(args.items, False, args.run_tag)
    filename = "run-health-2026-10-29.json" if args.evaluation else "pilot-health-2026-10-29.json"
    out = HERE / run_folder.name.replace("results", "analysis", 1) / filename
    report = health_report(args.items, args.run_tag, args.evaluation)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(HERE)}")
    for name, model in report["models"].items():
        print(
            name,
            "coverage",
            model["coverage_complete"],
            "request match",
            model["current_request_fingerprint_matches"],
            "problems",
            model["problems"],
        )
    projection = report["study_projection"]
    print("Selected-study projection; complete model coverage:", projection["complete_model_coverage"])
    print("Projected calls:", projection["calls"], "USD:", projection["usd"])
    print("With twice the output tokens:", projection["usd_double_output"])


if __name__ == "__main__":
    main()
