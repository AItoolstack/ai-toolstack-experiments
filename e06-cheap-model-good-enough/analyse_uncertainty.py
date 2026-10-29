"""Paired, task-stratified item bootstrap over frozen saved answers. No inference calls."""

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from analyse import answer_key, passes_check, score
from common import CONTROL_MODELS, MODEL_REPEATS, STUDY_MODELS, cost_usd, load_items, load_runs

ROOT = Path(__file__).resolve().parent


def observations(items, runs, model_names=STUDY_MODELS, fallback="sol"):
    """One observation per item/policy; keep all repeats together inside that observation."""
    indexed = {}
    for model in model_names:
        rows = [r for r in runs[model] if r["item"] in items]
        indexed[model] = {(r["item"], r["repeat"]): r for r in rows}
        required = {(i, rep) for i in items for rep in range(MODEL_REPEATS[model])}
        if len(rows) != len(required) or set(indexed[model]) != required:
            raise ValueError("Incomplete or duplicate cohort: " + model)
    vectors = defaultdict(list)
    ids = sorted(items)
    for ident in ids:
        item = items[ident]
        fr = indexed[fallback][ident, 0]
        fallback_right = float(score(item, fr)["correct"])
        fallback_cost = cost_usd(fallback, fr["prompt_tokens"], fr["completion_tokens"])
        for model in model_names:
            rows = [indexed[model][ident, rep] for rep in range(MODEL_REPEATS[model])]
            correct = [float(score(item, r)["correct"]) for r in rows]
            costs = [cost_usd(model, r["prompt_tokens"], r["completion_tokens"]) for r in rows]
            n = len(rows)
            vectors[model].append((sum(correct) / n, sum(costs) / n, 0.0))
            if model == fallback or model in CONTROL_MODELS:
                continue
            accept = [passes_check(item, r, "v2") for r in rows]
            vectors[model + ":check"].append(
                (
                    sum(right if keep else fallback_right for right, keep in zip(correct, accept, strict=True)) / n,
                    sum(cost + (0 if keep else fallback_cost) for cost, keep in zip(costs, accept, strict=True)) / n,
                    sum(not keep for keep in accept) / n,
                )
            )
            agree = len({answer_key(item, row) for row in rows}) == 1
            vectors[model + ":agreement"].append(
                (
                    correct[0] if agree else fallback_right,
                    sum(costs) + (0 if agree else fallback_cost),
                    float(not agree),
                )
            )
    return ids, dict(vectors)


def percentile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def interval(values):
    return [percentile(values, 0.025), percentile(values, 0.975)]


def bootstrap(ids, items, vectors, draws=10000, seed=6, fallback="sol"):
    if not ids or draws < 1:
        raise ValueError("A nonempty cohort and positive draws are required")
    strata = defaultdict(list)
    for index, ident in enumerate(ids):
        strata[items[ident]["task"]].append(index)
    n = len(ids)
    metrics = ["accuracy", "usd_per_1k", "escalated"]
    scales = [1, 1000, 1]
    sampled = {name: {metric: [] for metric in metrics} for name in vectors}
    differences = {name: {"accuracy_pp": [], "usd_per_1k": []} for name in vectors}
    rng = random.Random(seed)
    for _ in range(draws):
        selection = [i for task in sorted(strata) for i in rng.choices(strata[task], k=len(strata[task]))]
        base_acc = sum(vectors[fallback][i][0] for i in selection) / n
        base_cost = 1000 * sum(vectors[fallback][i][1] for i in selection) / n
        for name, rows in vectors.items():
            means = [scale * sum(rows[i][column] for i in selection) / n for column, scale in enumerate(scales)]
            for metric, value in zip(metrics, means, strict=True):
                sampled[name][metric].append(value)
            differences[name]["accuracy_pp"].append(100 * (means[0] - base_acc))
            differences[name]["usd_per_1k"].append(means[1] - base_cost)
    points = {}
    base_acc = sum(row[0] for row in vectors[fallback]) / n
    base_cost = 1000 * sum(row[1] for row in vectors[fallback]) / n
    for name, rows in vectors.items():
        point = {
            metric: scale * sum(row[col] for row in rows) / n
            for col, (metric, scale) in enumerate(zip(metrics, scales, strict=True))
        }
        points[name] = {
            "n_items": n,
            **point,
            "ci95": {metric: interval(sampled[name][metric]) for metric in metrics},
            "vs_sol": {
                "accuracy_difference_pp": 100 * (point["accuracy"] - base_acc),
                "accuracy_difference_pp_ci95": interval(differences[name]["accuracy_pp"]),
                "cost_difference_usd_per_1k": point["usd_per_1k"] - base_cost,
                "cost_difference_usd_per_1k_ci95": interval(differences[name]["usd_per_1k"]),
            },
        }
    return {"n_items": n, "strata": {task: len(group) for task, group in strata.items()}, "policies": points}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", choices=("all", "heldout", "development"), default="heldout")
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=6)
    args = parser.parse_args()
    items = load_items("items.jsonl")
    manifest = json.loads((ROOT / "dataset-manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256((ROOT / "items.jsonl").read_bytes()).hexdigest() != manifest["items_sha256"]:
        raise ValueError("Dataset/manifest mismatch")
    if args.cohort != "all":
        selected = set(manifest["held_out_ids" if args.cohort == "heldout" else "development_ids"])
        items = {i: item for i, item in items.items() if i in selected}
    runs = load_runs("items.jsonl", False, "frozen_20261029")
    ids, vectors = observations(items, runs)
    suffix = "" if args.cohort == "all" else "_" + args.cohort
    out = ROOT / ("analysis_frozen_20261029" + suffix)
    source = json.loads((out / "summary-v2.json").read_text(encoding="utf-8"))
    for name, rows in vectors.items():
        if ":" in name:
            model, mode = name.split(":")
            reference = source["cascades"][model]["all"][mode]
            reference_cost = reference["usd_per_1k_items"]
        else:
            reference = source["models"][name]["all"]
            reference_cost = reference["usd_per_1k"]
        if abs(sum(r[0] for r in rows) / len(rows) - reference["accuracy"]) > 1e-12:
            raise ValueError("Frozen accuracy mismatch: " + name)
        if abs(1000 * sum(r[1] for r in rows) / len(rows) - reference_cost) > 1e-12:
            raise ValueError("Frozen cost mismatch: " + name)
    results = {
        "run_date": "2026-10-29",
        "cohort": args.cohort,
        "draws": args.draws,
        "seed": args.seed,
        "method": "Task-stratified paired percentile bootstrap of whole items; all repeats kept together.",
        "provenance": {
            **source["provenance"],
            "bootstrap_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "overall": bootstrap(ids, items, vectors, args.draws, args.seed),
        "tasks": {},
        "limits": [
            "Item bootstrap does not capture all template/policy-document dependence.",
            "One Sol response per item; its sampling variation is unmeasured.",
            "Intervals do not establish production reliability or equivalence.",
        ],
    }
    for task in sorted({i["task"] for i in items.values()}):
        subset = [index for index, ident in enumerate(ids) if items[ident]["task"] == task]
        task_ids = [ids[i] for i in subset]
        task_vectors = {name: [rows[i] for i in subset] for name, rows in vectors.items()}
        results["tasks"][task] = bootstrap(task_ids, items, task_vectors, args.draws, args.seed)
    (out / "uncertainty.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {out.name}/uncertainty.json; {len(ids)} paired items, {args.draws} draws.")


if __name__ == "__main__":
    main()
