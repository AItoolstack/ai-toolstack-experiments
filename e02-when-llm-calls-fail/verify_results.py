"""Independent final accounting audit: reads ledgers; never calls engine.simulate.

Reporting/verification supplement, not a changed experimental arm. Reuses the approved
E06 answer-key scorer; independently checks schedules, terminal choices, sums and one
10,000-draw paired uncertainty comparison from ledger-derived item observations.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import random
import statistics
import struct
from collections import Counter, defaultdict

from e2core import ROOT, canonical, config, default_response, detect, historical, legacy, load_inputs, sha, write_json
from freeze import require_approval

OUTCOMES = ("correct", "wrong", "unverified", "couldnt_check")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b, message):
    require(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9), f"{message}: {a} != {b}")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def draw(parts):
    # An independent implementation of the exact published 53-bit hash convention.
    bytes_value = hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(",", ":")).encode()).digest()
    return (int.from_bytes(bytes_value[:8], "big") // 2048) / 9007199254740992


def expected_injection(scenario, row, event):
    if scenario["rate"] == 0:
        return None
    role, attempt = event["role"], event["attempt"]
    if scenario["regime"] == "persistent_shared" or (scenario["regime"] == "persistent_primary" and role == "primary"):
        role, attempt = "primary", 0
    return (
        scenario["failure"]
        if draw([row["seed"], row["item"], row["track"], role, attempt]) < scenario["rate"]
        else None
    )


def audit_attempt(row, event, scenario, data, cfg):
    role = event["role"]
    model = cfg[role]
    repeat = row["track"] if role == "primary" else 0
    source = data.runs[model][row["item"], repeat]
    require(event["model"] == model and event["source_repeat"] == repeat, "Attempt identity")
    require(event["source"] == data.refs[model, row["item"], repeat], "Source file/line reference")
    injected = expected_injection(scenario, row, event)
    require(event["injected"] == injected, "Failure schedule mismatch")
    require(event["native_fault"] == detect(row["task"], source), "Native response classification")
    require(bool(event["observed_failure"]) == bool(injected or event["native_fault"]), "Observed failure accounting")
    observed = (
        ("bad_arguments_json" if row["task"] == "tool" else "malformed_json")
        if injected == "malformed_json"
        else injected
    )
    require(event["observed_failure"] == (observed or event["native_fault"]), "Observed failure reason")
    input_price, output_price = historical.PRICES[model]
    cost = (source["prompt_tokens"] * input_price + source["completion_tokens"] * output_price) / 1e6
    low, high, seconds = cost, cost, source["latency_s"]
    if injected == "timeout":
        low, seconds = 0.0, cfg["timeout_seconds"]
    elif injected == "rate_limit":
        low, seconds = 0.0, cfg["rate_limit_seconds"]
    elif injected == "cutoff":
        low = high = (source["prompt_tokens"] * input_price + cfg["cutoff_output_tokens"] * output_price) / 1e6
    close(event["cost_low_usd"], low, "Attempt lower cost")
    close(event["cost_high_usd"], high, "Attempt upper cost")
    close(event["seconds"], seconds, "Attempt duration")
    close(event["accepted_response_usd"], cost if not event["observed_failure"] else 0, "Accepted response cost")


def grade(row, data, cache):
    output, item = row["output"], data.items[row["item"]]
    key = (row["item"], canonical(output))
    if key in cache:
        return cache[key]
    if output["kind"] == "unavailable":
        result = "couldnt_check"
    elif output["kind"] == "default" and item["task"] == "tool" and item["gold"]["call"] is None:
        result = "unverified"
    else:
        response = (
            default_response(item["task"], row["variant"])
            if output["kind"] == "default"
            else data.runs[output["model"]][row["item"], output["repeat"]]
        )
        result = "correct" if legacy.score(item, response)["correct"] else "wrong"
    cache[key] = result
    return result


def audit_terminal(row, cfg):
    events, design = row["events"], row["design"]
    primary = [e for e in events if e["role"] == "primary"]
    fallback = [e for e in events if e["role"] == "fallback"]
    require(0 < len(primary) <= cfg["primary_attempt_limits"][design], "Primary limit")
    require([e["attempt"] for e in primary] == list(range(len(primary))), "Primary attempt sequence")
    require(
        not fallback or (design == "fallback" and len(fallback) == 1 and fallback[0]["attempt"] == 0), "Fallback limit"
    )
    require(events == primary + fallback, "Attempt ordering")
    require(all(e["observed_failure"] for e in events[:-1]), "Continued after usable response")
    if fallback:
        require(
            len(primary) == cfg["primary_attempt_limits"][design] and primary[-1]["observed_failure"],
            "Fallback before primary exhaustion",
        )
    if events[-1]["observed_failure"]:
        require(len(primary) == cfg["primary_attempt_limits"][design], "Stopped early on failure")
        require(design != "fallback" or len(fallback) == 1, "Fallback not attempted")
        expected = "default" if design in ("default", "retry") else "unavailable"
        require(row["output"]["kind"] == expected, "Wrong exhaustion result")
    else:
        last = events[-1]
        require(
            row["output"] == {"kind": "source", "model": last["model"], "repeat": last["source_repeat"]},
            "Wrong accepted response",
        )
    require(row["status"] == ("couldnt_check" if row["output"]["kind"] == "unavailable" else "completed"), "UI status")
    require(row["calls"] == len(events), "Calls lost")
    backoff = sum(cfg["backoff_seconds"][: len(primary) - 1])
    close(row["backoff_seconds"], backoff, "Backoff")
    close(row["latency_seconds"], backoff + sum(e["seconds"] for e in events), "Sequential latency")
    for name in ("cost_low_usd", "cost_high_usd", "accepted_response_usd"):
        close(row[name], sum(e[name] for e in events), "Cost sum")


def item_interval(values):
    ordered = sorted(values)
    result = []
    for probability in (0.025, 0.975):
        position = (len(ordered) - 1) * probability
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        result.append(ordered[low] + (position - low) * (ordered[high] - ordered[low]))
    return result


def check_bootstrap(item_values, summary, uncertainty, data, cfg, cohort):
    ids = sorted(data.cohorts[cohort])
    strata = {task: [i for i in ids if data.items[i]["task"] == task] for task in ("invoice", "rules", "tool")}
    rng = random.Random(cfg["bootstrap_seed"])
    series = {design: [] for design in cfg["designs"]}
    # Wrong-rate uncertainty for the prespecified headline comparison, independently resampled.
    for _ in range(10000):
        sample = [i for task in sorted(strata) for i in rng.choices(strata[task], k=len(strata[task]))]
        for design in cfg["designs"]:
            series[design].append(
                1000 * sum(item_values[design, i][0] / item_values[design, i][1] for i in sample) / len(ids)
            )
    for design in cfg["designs"]:
        target = uncertainty["scenarios"]["independent-20-timeout"]["zero_numeric"]["all"][design]["wrong_per_1000"]
        expected = item_interval(series[design])
        paired = item_interval([a - b for a, b in zip(series[design], series["default"], strict=True)])
        for actual, wanted in zip(target["item_ci95"], expected, strict=True):
            close(actual, wanted, "Independent item interval")
        for actual, wanted in zip(target["minus_default"]["item_ci95"], paired, strict=True):
            close(actual, wanted, "Independent paired interval")


def audit_cohort(cohort, data, cfg, review):
    run_dir, analysis_dir = ROOT / "results" / cohort, ROOT / "analysis" / cohort
    spec, progress = read(run_dir / "run.json"), read(run_dir / "progress.json")
    verification = read(analysis_dir / "verification.json")
    require(spec["review_sha256"] == review == verification["review_sha256"], "Approved snapshot")
    require(spec["item_ids"] == sorted(data.cohorts[cohort]), "Cohort mismatch")
    require(
        spec["config"] == cfg and spec["seeds"] == cfg["seeds"] and spec["tracks"] == cfg["primary_tracks"],
        "Seed/track/config mismatch",
    )
    require(spec["e06_input_sha256"] == data.hashes, "Input hash mismatch")
    for name, expected in verification["output_sha256"].items():
        require(sha(analysis_dir / name) == expected, "Analysis output hash: " + name)
    summary, uncertainty = read(analysis_dir / "summary.json"), read(analysis_dir / "uncertainty.json")
    stats = defaultdict(
        lambda: {
            "counts": Counter(),
            "calls": 0,
            "cost_low_usd": 0.0,
            "cost_high_usd": 0.0,
            "accepted_response_usd": 0.0,
            "latencies": [],
            "initial": 0,
            "injected": Counter(),
            "observed": Counter(),
            "items": set(),
            "transitions": Counter(),
        }
    )
    score_cache, baseline_cache, item_values = {}, {}, defaultdict(lambda: [0, 0])
    rows_total = 0
    candidates = []
    expected_names = {f"{scenario['id']}--{seed}.jsonl.gz" for scenario in spec["scenarios"] for seed in spec["seeds"]}
    require(set(progress["shards"]) == expected_names, "Shard count")
    for scenario in spec["scenarios"]:
        for seed in spec["seeds"]:
            name = f"{scenario['id']}--{seed}.jsonl.gz"
            path = run_dir / "shards" / name
            require(sha(path) == progress["shards"][name]["sha256"], "Shard hash")
            seen, count = set(), 0
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    count += 1
                    rows_total += 1
                    require(row["scenario"] == scenario["id"] and row["seed"] == seed, "Record identity")
                    key = (row["item"], row["track"], row["variant"], row["design"])
                    require(key not in seen, "Duplicate replay")
                    seen.add(key)
                    require(row["task"] == data.items[row["item"]]["task"], "Task identity")
                    audit_terminal(row, cfg)
                    for event in row["events"]:
                        audit_attempt(row, event, scenario, data, cfg)
                    result = grade(row, data, score_cache)
                    base_key = (row["item"], row["track"])
                    if base_key not in baseline_cache:
                        baseline_cache[base_key] = legacy.score(
                            data.items[row["item"]], data.runs[cfg["primary"]][base_key]
                        )["correct"]
                    base = baseline_cache[base_key]
                    if (
                        cohort == "heldout"
                        and scenario["id"] == "independent-05-timeout"
                        and row["variant"] == "zero_numeric"
                        and row["design"] == "default"
                        and base
                        and result == "wrong"
                    ):
                        candidates.append(row)
                    if scenario["id"] == "independent-20-timeout" and row["variant"] == "zero_numeric":
                        item_values[row["design"], row["item"]][0] += result == "wrong"
                        item_values[row["design"], row["item"]][1] += 1
                    for scope in ("all", row["task"]):
                        stat = stats[scenario["id"], row["variant"], scope, row["design"]]
                        stat["counts"][result] += 1
                        stat["calls"] += row["calls"]
                        stat["items"].add(row["item"])
                        stat["latencies"].append(row["latency_seconds"])
                        stat["initial"] += bool(row["events"][0]["injected"])
                        for field in ("cost_low_usd", "cost_high_usd", "accepted_response_usd"):
                            stat[field] += row[field]
                        stat["transitions"]["introduced_wrong"] += base and result == "wrong"
                        stat["transitions"]["inherited_wrong"] += not base and result == "wrong"
                        stat["transitions"]["recovered"] += not base and result == "correct"
                        for event in row["events"]:
                            if event["injected"]:
                                stat["injected"][event["injected"]] += 1
                            if event["observed_failure"]:
                                stat["observed"][event["observed_failure"]] += 1
            expected = {
                (ident, track, variant, design)
                for ident in spec["item_ids"]
                for track in spec["tracks"]
                for variant in cfg["default_variants"]
                for design in cfg["designs"]
            }
            require(seen == expected and count == progress["shards"][name]["rows"], "Replay coverage")
    for (scenario, variant, scope, design), stat in stats.items():
        target = summary["scenarios"][scenario][variant][scope][design]
        denom = sum(stat["counts"].values())
        require(target["counts"] == {key: stat["counts"][key] for key in OUTCOMES}, "Outcome counts")
        require(
            target["denominator_replays"] == denom and target["distinct_items"] == len(stat["items"]), "Denominator"
        )
        require(target["total_calls"] == stat["calls"], "Total calls")
        require(target["initial_injected_tasks"] == stat["initial"], "Initial failures")
        require(target["injected_attempts_by_type"] == dict(stat["injected"]), "Injected failures")
        require(target["observed_failure_reasons"] == dict(stat["observed"]), "Observed failures")
        require(target["transition_counts"] == dict(stat["transitions"]), "Error transitions")
        for metric in OUTCOMES:
            close(target["point"][metric + "_per_1000"], 1000 * stat["counts"][metric] / denom, "Outcome rate")
        close(target["point"]["mean_calls"], stat["calls"] / denom, "Mean calls")
        close(target["point"]["mean_latency_seconds"], statistics.fmean(stat["latencies"]), "Mean time")
        sorted_times = sorted(stat["latencies"])
        position = (len(sorted_times) - 1) * 0.95
        low = int(position)
        high = min(low + 1, len(sorted_times) - 1)
        p95 = sorted_times[low] + (position - low) * (sorted_times[high] - sorted_times[low])
        close(target["modelled_p95_seconds"], p95, "Modelled p95 time")
        for field in ("cost_low_usd", "cost_high_usd", "accepted_response_usd"):
            close(target["point"][field + "_per_1000"], 1000 * stat[field] / denom, "Per-1000 cost")
        for metric, result in uncertainty["scenarios"][scenario][variant][scope][design].items():
            close(result["point"], target["point"][metric], "Uncertainty point")
            close(
                result["minus_default"]["point"],
                result["point"] - summary["scenarios"][scenario][variant][scope]["default"]["point"][metric],
                "Paired default point",
            )
            close(
                result["minus_own_control"]["point"],
                result["point"] - summary["scenarios"]["control"][variant][scope][design]["point"][metric],
                "Paired control point",
            )
    candidates.sort(key=lambda row: (row["item"], row["seed"], row["track"]))
    saved_candidates = [
        json.loads(line) for line in (analysis_dir / "example-candidates.jsonl").read_text().splitlines()
    ]
    require(saved_candidates == candidates, "Example candidate rule")
    example = read(analysis_dir / "example.json")
    if candidates:
        require(
            example["selection"]
            == {key: candidates[0][key] for key in ("item", "scenario", "seed", "track", "variant")},
            "First example rule",
        )
    else:
        require(example is None, "Unexpected substitute example")
    check_bootstrap(item_values, summary, uncertainty, data, cfg, cohort)
    # These equalities are expected from the model; check before explaining them as such.
    for scenario in spec["scenarios"]:
        for scope in ("all", "invoice", "tool", "rules"):
            for design in cfg["designs"]:
                a = summary["scenarios"][scenario["id"]]["zero_numeric"][scope][design]
                b = summary["scenarios"][scenario["id"]]["all_null"][scope][design]
                require(a["counts"] == b["counts"], "Unexpected whole-task default sensitivity; revise narrative")
            if scenario["regime"] == "persistent_shared":
                a = summary["scenarios"][scenario["id"]]["zero_numeric"][scope]
                require(
                    a["fallback"]["counts"] == a["say_so"]["counts"], "Unexpected shared-failure outcome difference"
                )
    require(rows_total == verification["ledger_rows_verified"], "Verified row total")
    print(f"Independent audit passed: {cohort}, {rows_total:,} records, {len(stats)} summary groups.", flush=True)
    return {
        "rows": rows_total,
        "summary_groups": len(stats),
        "shards": len(expected_names),
        "verification_sha256": sha(analysis_dir / "verification.json"),
        "independent_bootstrap_draws": 10000,
    }


def cached_audit(cohort, data, cfg, review):
    """Resume only when every raw/analysed byte and this audit's source are unchanged."""
    run_dir, analysis_dir = ROOT / "results" / cohort, ROOT / "analysis" / cohort
    progress = read(run_dir / "progress.json")
    verification = read(analysis_dir / "verification.json")
    paths = [run_dir / "run.json", run_dir / "progress.json", analysis_dir / "verification.json"]
    paths += [run_dir / "shards" / name for name in sorted(progress["shards"])]
    paths += [analysis_dir / name for name in sorted(verification["output_sha256"])]
    fingerprint = {
        "review_sha256": review,
        "audit_source_sha256": sha(ROOT / "verify_results.py"),
        "e06_input_sha256": data.hashes,
        "files": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in paths},
    }
    cache_path = ROOT / "audit" / (cohort + ".json")
    if cache_path.exists():
        cached = read(cache_path)
        if cached["fingerprint"] == fingerprint:
            print("Independent audit reverified against all file hashes: " + cohort, flush=True)
            return cached["result"]
    result = audit_cohort(cohort, data, cfg, review)
    write_json(cache_path, {"fingerprint": fingerprint, "result": result})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cohort",
        choices=("heldout", "development"),
        help="Audit one completed cohort now; final validation later rechecks every file hash",
    )
    args = parser.parse_args()
    review = require_approval()
    data, cfg = load_inputs(), config()
    if args.cohort:
        cached_audit(args.cohort, data, cfg, review)
        return
    cohorts = {name: cached_audit(name, data, cfg, review) for name in ("heldout", "development")}
    reporting = read(ROOT / "REPORTING.json")
    require(reporting["review_sha256"] == review, "Reporting review")
    for name, expected in reporting["outputs"].items():
        require(sha(ROOT / name) == expected, "Report changed: " + name)
    for claim in read(ROOT / "claims.json"):
        for source in claim["sources"]:
            value = read(ROOT / source["file"])
            for field in source["path"]:
                value = value[field]
            require(value == source["value"], "Claim source mismatch")
    for basename, expected_height in (("e02-recovery-flow", 1344), ("e02-wrong-results", 1068)):
        raw = (ROOT / "figures-post" / (basename + ".png")).read_bytes()
        require(struct.unpack(">II", raw[16:24]) == (960, expected_height), "Figure canvas dimensions")
    chart_meta = read(ROOT / "figures-post/e02-wrong-results.json")
    require(chart_meta["summary_sha256"] == sha(ROOT / "analysis/heldout/summary.json"), "Chart data source")
    write_json(
        ROOT / "FINAL-VALIDATION.json",
        {
            "status": "PASS",
            "review_sha256": review,
            "approval_sha256": sha(ROOT / "APPROVAL.json"),
            "cohorts": cohorts,
            "api_calls": 0,
            "verifier_sha256": sha(ROOT / "verify_results.py"),
            "reporting_sha256": sha(ROOT / "REPORTING.json"),
            "figures_sha256": {p.name: sha(p) for p in sorted((ROOT / "figures-post").glob("e02-*"))},
            "note": "Independent audit of all ledger schedules/terminals/accounting and representative paired CIs. "
            "No new experiment, no changed protocol, and no production inference.",
        },
    )
    print("Final source/claim/figure audit passed; wrote FINAL-VALIDATION.json.")


if __name__ == "__main__":
    main()
