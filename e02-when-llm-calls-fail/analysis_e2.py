"""Code scoring, replay-ledger verification and paired item uncertainty for E02."""

from __future__ import annotations

import gzip
import itertools
import json
import os
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from e2core import ROOT, canonical, config, digest, legacy, load_inputs, sha, write_json
from engine import response_for
from freeze import check, require_approval
from run import run_spec, shard_records

OUTCOMES = ("correct", "wrong", "unverified", "couldnt_check")
METRICS = (*OUTCOMES, "calls", "cost_low_usd", "cost_high_usd", "latency_seconds")
TRANSITIONS = ("introduced_wrong", "inherited_wrong", "recovered")
ADDITIONAL = (*TRANSITIONS, "accepted_response_usd")
ALL_METRICS = (*METRICS, *ADDITIONAL)
RATE_METRICS = set(OUTCOMES) | set(TRANSITIONS)


def percentile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def interval(values):
    return [percentile(values, 0.025), percentile(values, 0.975)]


def scale(metric):
    return 1000 if metric in RATE_METRICS or "usd" in metric else 1


def metric_label(metric):
    if metric in RATE_METRICS:
        return metric + "_per_1000"
    if "usd" in metric:
        return metric + "_per_1000"
    return "mean_" + metric


def outcome(record, item, response):
    if record["output"]["kind"] == "unavailable":
        return "couldnt_check"
    if record["output"]["kind"] == "default" and item["task"] == "tool" and item["gold"]["call"] is None:
        return "unverified"
    return "correct" if legacy.score(item, response)["correct"] else "wrong"


def selections(ids, data, draws, seed):
    """Same task-stratified paired draws for every policy and scenario in this scope."""
    strata = defaultdict(list)
    for index, ident in enumerate(ids):
        strata[data.items[ident]["task"]].append(index)
    rng = random.Random(seed)
    return [
        [index for task in sorted(strata) for index in rng.choices(strata[task], k=len(strata[task]))]
        for _ in range(draws)
    ]


def bootstrap_vectors(vectors, selected):
    """Use C-level map/sum over precomputed columns; keep dependencies within each item."""
    result = {}
    for design, rows in vectors.items():
        columns = list(zip(*rows, strict=True))
        result[design] = {}
        for index, metric in enumerate(METRICS):
            column = columns[index]
            factor = scale(metric) / len(rows)
            result[design][metric] = [factor * sum(map(column.__getitem__, sample)) for sample in selected]
    return result


def verified_rows(run_dir: Path, data):
    spec = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    pilot = spec["mode"] == "development_pilot"
    review = check() if pilot else require_approval()
    expected_spec = run_spec(data, config(), pilot, "development" if pilot else spec["cohort"], review)
    if spec != expected_spec:
        raise ValueError("Analysis refused: run manifest differs from pinned configuration/cohort/inputs")
    progress = json.loads((run_dir / "progress.json").read_text(encoding="utf-8"))
    if progress["spec_sha256"] != digest(spec):
        raise ValueError("Run progress mismatch")
    expected_names = {f"{s['id']}--{seed}.jsonl.gz" for s in spec["scenarios"] for seed in spec["seeds"]}
    if set(progress["shards"]) != expected_names:
        raise ValueError("Incomplete or unexpected run shards")
    if {p.name for p in (run_dir / "shards").glob("*.jsonl.gz")} != expected_names:
        raise ValueError("Unindexed or missing run shard")

    def records():
        for scenario in spec["scenarios"]:
            for seed in spec["seeds"]:
                name = f"{scenario['id']}--{seed}.jsonl.gz"
                path = run_dir / "shards" / name
                entry = progress["shards"][name]
                if sha(path) != entry["sha256"]:
                    raise ValueError("Corrupt/changed shard: " + name)
                count = 0
                with gzip.open(path, "rt", encoding="utf-8") as stream:
                    saved = (json.loads(line) for line in stream)
                    expected = shard_records(spec, scenario, seed, data)
                    for row, rebuilt in itertools.zip_longest(saved, expected):
                        if row != rebuilt:
                            raise ValueError("Replay/accounting/coverage mismatch: " + name)
                        count += 1
                        yield row
                if count != entry["rows"]:
                    raise ValueError("Shard row count mismatch")

    return spec, progress, records()


def score_records(records, data, cfg):
    sums, counts = {}, Counter()
    stats = defaultdict(
        lambda: {
            "outcomes": Counter(),
            "transitions": Counter(),
            "calls": 0,
            "injected": Counter(),
            "observed": Counter(),
            "native": Counter(),
            "initial_injected": 0,
            "latencies": [],
            "items": set(),
            "injected_tasks": 0,
            "cost_low_usd": 0.0,
            "cost_high_usd": 0.0,
            "accepted_response_usd": 0.0,
            "backoff_seconds": 0.0,
        }
    )
    seed_sums, seed_counts = {}, Counter()
    score_cache, base_cache = {}, {}
    example_candidates, pilot_candidates = [], []
    ledger_rows = 0
    for record in records:
        ledger_rows += 1
        ident = record["item"]
        item = data.items[ident]
        out_key = (ident, canonical(record["output"]))
        if out_key not in score_cache:
            score_cache[out_key] = outcome(record, item, response_for(record, data))
        graded = score_cache[out_key]
        base_key = (ident, record["track"])
        if base_key not in base_cache:
            base_cache[base_key] = legacy.score(item, data.runs[cfg["primary"]][base_key])["correct"]
        base_correct = base_cache[base_key]
        measures = {name: float(graded == name) for name in OUTCOMES}
        measures.update({name: record[name] for name in METRICS if name not in OUTCOMES})
        measures.update(
            introduced_wrong=float(base_correct and graded == "wrong"),
            inherited_wrong=float(not base_correct and graded == "wrong"),
            recovered=float(not base_correct and graded == "correct"),
            accepted_response_usd=record["accepted_response_usd"],
        )
        vector = [measures[name] for name in ALL_METRICS]
        group = (record["scenario"], record["variant"], record["design"])
        key = (*group, ident)
        sums.setdefault(key, [0.0] * len(ALL_METRICS))
        sums[key] = [a + b for a, b in zip(sums[key], vector, strict=True)]
        counts[key] += 1
        for scope in ("all", item["task"]):
            skey = (*group, scope, record["seed"])
            seed_sums.setdefault(skey, [0.0] * len(ALL_METRICS))
            seed_sums[skey] = [a + b for a, b in zip(seed_sums[skey], vector, strict=True)]
            seed_counts[skey] += 1
            stat = stats[(*group, scope)]
            stat["outcomes"][graded] += 1
            stat["items"].add(ident)
            stat["calls"] += record["calls"]
            stat["backoff_seconds"] += record["backoff_seconds"]
            stat["initial_injected"] += bool(record["events"][0]["injected"])
            stat["injected_tasks"] += any(e["injected"] for e in record["events"])
            stat["latencies"].append(record["latency_seconds"])
            for name in ("cost_low_usd", "cost_high_usd", "accepted_response_usd"):
                stat[name] += record[name]
            stat["transitions"].update({name: int(measures[name]) for name in TRANSITIONS})
            for event in record["events"]:
                if event["injected"]:
                    stat["injected"][event["injected"]] += 1
                if event["observed_failure"]:
                    stat["observed"][event["observed_failure"]] += 1
                if event["native_fault"]:
                    stat["native"][event["native_fault"]] += 1
        if record["variant"] == "zero_numeric" and record["design"] == "default":
            if (
                record["scenario"] == "independent-05-timeout"
                and base_correct
                and graded == "wrong"
                and ident in data.cohorts["heldout"]
            ):
                example_candidates.append(record)
            if record["output"]["kind"] == "default":
                pilot_candidates.append(record)
    vectors = {key: [v / counts[key] for v in values] for key, values in sums.items()}
    return vectors, stats, seed_sums, seed_counts, example_candidates, pilot_candidates, ledger_rows


def summarise(spec, vectors, stats, seed_sums, seed_counts, data, draws):
    summary, uncertainty = {}, {}
    cfg = spec["config"]
    control_boot, selected_cache = {}, {}
    for scenario in spec["scenarios"]:
        scenario_id = scenario["id"]
        summary[scenario_id], uncertainty[scenario_id] = {}, {}
        for variant in cfg["default_variants"]:
            summary[scenario_id][variant], uncertainty[scenario_id][variant] = {}, {}
            for scope in ("all", "invoice", "tool", "rules"):
                ids = sorted(i for i in spec["item_ids"] if scope == "all" or data.items[i]["task"] == scope)
                if not ids:
                    continue
                if scope not in selected_cache:
                    selected_cache[scope] = selections(ids, data, draws, cfg["bootstrap_seed"])
                policy_vectors = {
                    design: [vectors[scenario_id, variant, design, ident] for ident in ids] for design in cfg["designs"]
                }
                boot = bootstrap_vectors(policy_vectors, selected_cache[scope])
                if scenario_id == "control":
                    control_boot[variant, scope] = boot
                summary[scenario_id][variant][scope], uncertainty[scenario_id][variant][scope] = {}, {}
                for design, rows in policy_vectors.items():
                    group = (scenario_id, variant, design, scope)
                    stat = stats[group]
                    n = sum(stat["outcomes"].values())
                    if n != len(ids) * len(spec["seeds"]) * len(spec["tracks"]):
                        raise ValueError("Unequal item/seed/track coverage")
                    if (
                        stat["transitions"]["introduced_wrong"] + stat["transitions"]["inherited_wrong"]
                        != stat["outcomes"]["wrong"]
                    ):
                        raise ValueError("Wrong-result transition accounting failed")
                    points = {
                        metric_label(metric): scale(metric) * statistics.fmean(r[index] for r in rows)
                        for index, metric in enumerate(ALL_METRICS)
                    }
                    seed_ranges = {}
                    for index, metric in enumerate(METRICS):
                        seed_means = [
                            scale(metric) * seed_sums[(*group, seed)][index] / seed_counts[(*group, seed)]
                            for seed in spec["seeds"]
                        ]
                        seed_ranges[metric_label(metric)] = [min(seed_means), max(seed_means)]
                    summary[scenario_id][variant][scope][design] = {
                        "counts": {name: stat["outcomes"][name] for name in OUTCOMES},
                        "denominator_replays": n,
                        "distinct_items": len(ids),
                        "point": points,
                        "possibly_misleading_completed_bounds_count": [
                            stat["outcomes"]["wrong"],
                            stat["outcomes"]["wrong"] + stat["outcomes"]["unverified"],
                        ],
                        "transition_counts": dict(stat["transitions"]),
                        "total_calls": stat["calls"],
                        "extra_calls_over_one": stat["calls"] - n,
                        "injected_attempts_by_type": dict(stat["injected"]),
                        "observed_failure_reasons": dict(stat["observed"]),
                        "source_native_faults_on_attempts": dict(stat["native"]),
                        "initial_injected_tasks": stat["initial_injected"],
                        "tasks_with_any_injected_failure": stat["injected_tasks"],
                        "realised_initial_injected_fraction": stat["initial_injected"] / n,
                        "realised_injected_attempt_fraction": sum(stat["injected"].values()) / stat["calls"],
                        "realised_observed_failure_attempt_fraction": sum(stat["observed"].values()) / stat["calls"],
                        "modelled_p95_seconds": percentile(stat["latencies"], 0.95),
                        "total_backoff_seconds": stat["backoff_seconds"],
                        "total_cost_low_usd": stat["cost_low_usd"],
                        "total_cost_high_usd": stat["cost_high_usd"],
                        "total_accepted_response_usd": stat["accepted_response_usd"],
                        "monte_carlo_seed_mean_min_max": seed_ranges,
                    }
                    estimates = {}
                    for metric in METRICS:
                        values = boot[design][metric]
                        default_values = boot["default"][metric]
                        control_values = control_boot[variant, scope][design][metric]
                        label = metric_label(metric)
                        default_point = scale(metric) * statistics.fmean(
                            r[METRICS.index(metric)] for r in policy_vectors["default"]
                        )
                        control_point = scale(metric) * statistics.fmean(
                            vectors["control", variant, design, ident][METRICS.index(metric)] for ident in ids
                        )
                        estimates[label] = {
                            "point": points[label],
                            "item_ci95": interval(values),
                            "minus_default": {
                                "point": points[label] - default_point,
                                "item_ci95": interval([a - b for a, b in zip(values, default_values, strict=True)]),
                            },
                            "minus_own_control": {
                                "point": points[label] - control_point,
                                "item_ci95": interval([a - b for a, b in zip(values, control_values, strict=True)]),
                            },
                        }
                    uncertainty[scenario_id][variant][scope][design] = estimates
    return summary, uncertainty


def display_example(record, spec, data):
    from run import shard_records

    scenario = next(s for s in spec["scenarios"] if s["id"] == record["scenario"])
    paired = [
        r
        for r in shard_records(spec, scenario, record["seed"], data)
        if r["item"] == record["item"] and r["track"] == record["track"] and r["variant"] == record["variant"]
    ]
    return {
        "selection": {k: record[k] for k in ("item", "scenario", "seed", "track", "variant")},
        "synthetic_task": data.items[record["item"]],
        "paired_designs": [
            {
                "record": r,
                "visible_response": {
                    k: response_for(r, data).get(k) for k in ("content", "tool_calls", "finish_reason")
                },
                "grade": outcome(r, data.items[r["item"]], response_for(r, data)),
            }
            for r in paired
        ],
    }


def write_reports(out, spec, summary, example, ledger_rows):
    pilot = spec["mode"] == "development_pilot"
    chosen = "independent-20-timeout"
    table = summary[chosen]["zero_numeric"]["all"]
    lines = [
        "# E02 development pilot" if pilot else "# E02 full results",
        "",
        "Status: DEVELOPMENT ONLY; not a publication result."
        if pilot
        else "Status: approved offline evaluation; modelled failure scenarios, not observed provider reliability.",
        "",
        f"Cohort: {spec['cohort']}; {len(spec['item_ids'])} distinct items; "
        f"{len(spec['seeds'])} seeds; {len(spec['tracks'])} replay tracks.",
        f"Verified {ledger_rows:,} ledger records by deterministic replay. API calls: 0.",
        "",
        "The table below is one specified scenario: independent 20% timeout, zero-numeric defaults.",
        "All 46 scenarios, both variants and task breakdowns are in summary.json.",
        "",
        "| Design | Correct | Wrong | Unverified | Couldn't check | Calls | Modelled mean seconds |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for design in spec["config"]["designs"]:
        row = table[design]
        counts = row["counts"]
        denom = row["denominator_replays"]
        cells = [f"{counts[name]}/{denom}" for name in OUTCOMES]
        lines.append(
            f"| {design} | "
            + " | ".join(cells)
            + f" | {row['total_calls']} | {row['point']['mean_latency_seconds']:.3f} |"
        )
    lines += [
        "",
        "Counts reuse the same items and responses. They are not independent trials.",
        "Intervals and paired differences are in uncertainty.json; pilot intervals are diagnostic only.",
        "Cost values are historical token-price proxies; time includes assumed failure durations/backoff.",
        "",
        "## Example",
        "",
        (
            f"Selected item: {example['selection']['item']}; see example.json for source lines, "
            "visible outputs and all four paired designs."
        )
        if example
        else "No example satisfied the fixed selection rule.",
        "",
        "## Limits",
        "",
        "Synthetic and partly templated tasks; one reused fallback response; structural detection cannot",
        "establish factual correctness; no-call prose has coarse grading; defaults and failure persistence",
        "are assumptions; no business tools execute; no queues or live provider failures are measured.",
        "Do not present seed repetitions as additional items or cost bounds as invoices.",
        "These failure rates are assumptions, not production measurements.",
        "",
        "## Evidence",
        "",
        "- summary.json: scenario -> default variant -> task/all -> design; counts, denominator and point metrics.",
        "- uncertainty.json: same paths; item intervals and paired differences, plus method metadata.",
        "- verification.json: exact run, input, review, shard and analysis-code hashes.",
        "- The input run's shards: every attempt and terminal result, source file/line references and accounting.",
        "- example-candidates.jsonl: all examples meeting the primary rule.",
        "- example.json: selected paired trace; pilot-trace-candidates.jsonl: separate development trace candidates.",
        "",
    ]
    filename = "PILOT-REPORT.md" if pilot else "FULL-RESULTS.md"
    (out / filename).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    if not pilot:
        claims, handover = (
            ["# E02 claim-to-source map", "", "All claims are scenario-conditional.", ""],
            [
                "# Handover for the post",
                "",
                "Do not pool scenarios into a production claim.",
                "",
                "The following preselected comparison uses independent 20% timeout and zero-numeric defaults.",
                "",
            ],
        )
        for design in spec["config"]["designs"]:
            row = table[design]
            path = f"summary.json::{chosen}.zero_numeric.all.{design}"
            statement = (
                f"{design}: {row['counts']['wrong']}/{row['denominator_replays']} wrong completed results; "
                f"{row['counts']['couldnt_check']}/{row['denominator_replays']} couldn't-check results; "
                f"{row['total_calls']} calls."
            )
            claims += [f"- {statement} Source: `{path}`; fields `counts`, `denominator_replays`, `total_calls`."]
            handover += [f"- {statement} Source: `{path}`; read matching uncertainty.json before comparing."]
        handover += [
            "",
            "## Example rule",
            "",
            "First baseline-correct -> wrong default at independent 5% timeout, ordered item, seed, track.",
            "See example-candidates.jsonl and example.json. If none qualify, do not substitute a dramatic case.",
            "",
            "## What not to claim",
            "",
            "No measured production failure rates, real retry recovery, queue congestion, provider billing,",
            "universal best policy, or proof that structural checks establish truth. Report unverified tool defaults.",
            "Read DESIGN.md and FULL-RESULTS.md limits; manually review every publication claim.",
            "",
        ]
        (out / "RESULTS.md").write_text("\n".join(claims) + "\n", encoding="utf-8", newline="\n")
        (out / "HANDOVER-FOR-POST.md").write_text("\n".join(handover), encoding="utf-8", newline="\n")


def analyse(run_dir: Path, out: Path):
    if out.resolve() == run_dir.resolve() or run_dir.resolve() in out.resolve().parents:
        raise ValueError("Analysis output must be separate from immutable run records")
    data = load_inputs()
    spec, progress, records = verified_rows(run_dir, data)
    pilot = spec["mode"] == "development_pilot"
    draws = 200 if pilot else spec["config"]["bootstrap_draws"]
    vectors, stats, seed_sums, seed_counts, candidates, pilot_candidates, ledger_rows = score_records(
        records, data, spec["config"]
    )
    summary, uncertainty = summarise(spec, vectors, stats, seed_sums, seed_counts, data, draws)
    candidates.sort(key=lambda r: (r["item"], r["seed"], r["track"]))
    selected = candidates[0] if candidates else None
    if pilot:
        # Pilot trace is an engineering diagnostic, explicitly separate from the full example rule.
        pilot_candidates.sort(key=lambda r: (r["scenario"], r["item"], r["seed"], r["track"]))
        selected = pilot_candidates[0] if pilot_candidates else None
    example = display_example(selected, spec, data) if selected else None
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "summary.json", {"mode": spec["mode"], "cohort": spec["cohort"], "scenarios": summary})
    write_json(
        out / "uncertainty.json",
        {
            "method": {
                "unit": "whole item; all seeds/tracks retained together",
                "task_stratified": True,
                "draws": draws,
                "seed": spec["config"]["bootstrap_seed"],
                "interval": "percentile 95%",
                "pilot_diagnostic_only": pilot,
                "monte_carlo": "seed min/max in summary; not a confidence interval",
                "limits": "Conditional on templates, fixed saved answers, failure/cost/time/default assumptions.",
            },
            "scenarios": uncertainty,
        },
    )
    write_json(out / "example.json", example)
    (out / "example-candidates.jsonl").write_text(
        "".join(canonical(r) + "\n" for r in candidates), encoding="utf-8", newline="\n"
    )
    if pilot:
        (out / "pilot-trace-candidates.jsonl").write_text(
            "".join(canonical(r) + "\n" for r in pilot_candidates), encoding="utf-8", newline="\n"
        )
    write_reports(out, spec, summary, example, ledger_rows)
    write_json(
        out / "verification.json",
        {
            "run_manifest_sha256": sha(run_dir / "run.json"),
            "run_spec_sha256": digest(spec),
            "run_directory_relative_to_e02": os.path.relpath(run_dir, ROOT).replace("\\", "/"),
            "progress": progress,
            "review_sha256": spec["review_sha256"],
            "source_hashes": {
                name: sha(ROOT / name) for name in ("analysis_e2.py", "analyse.py", "engine.py", "e2core.py")
            },
            "e06_input_sha256": data.hashes,
            "ledger_rows_verified": ledger_rows,
            "output_sha256": {
                p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "verification.json"
            },
            "all_rows_replayed_and_compared": True,
            "api_calls": 0,
        },
    )
    print(
        f"Scored {ledger_rows:,} verified records; {len(spec['item_ids'])} distinct {spec['cohort']} items; "
        f"{draws} paired item-bootstrap draws. {'PILOT ONLY.' if pilot else 'Approved evaluation.'}"
    )
