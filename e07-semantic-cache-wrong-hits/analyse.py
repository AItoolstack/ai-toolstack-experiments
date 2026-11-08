"""Score saved vectors deterministically. This command never calls a model."""
import argparse
import json

import numpy as np
from common import HERE, THRESHOLDS, atomic_json, digest, guard_passes, read_jsonl, validate_vector
from freeze import check
from threadpoolctl import threadpool_limits


@threadpool_limits.wrap(limits=1, user_api="blas")
def score(model, dry_run=False):
    base = HERE / "development/full-fixture" / digest(HERE / "cache.jsonl")[:12] if dry_run else HERE / "results"
    root = base / model
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Run is incomplete.")
    identity = manifest["identity"]
    if (identity["items_sha256"] != digest(HERE / "items.jsonl") or
            identity["cache_sha256"] != digest(HERE / "cache.jsonl")):
        raise ValueError("Run data differs from current inputs.")
    if not dry_run and identity["freeze_sha256"] != digest(HERE / "FREEZE.json"):
        raise ValueError("Run was produced against a different freeze.")
    items = read_jsonl(HERE / "items.jsonl")
    cache = read_jsonl(HERE / "cache.jsonl")
    records = json.loads((root / "embeddings.json").read_text())
    if len({row["text"] for row in records}) != len(records):
        raise ValueError("Duplicate saved embeddings.")
    for row in records:
        validate_vector(row["vector"], identity["spec"]["dimensions"])
    vectors = {row["text"]: np.asarray(row["vector"], dtype=float) for row in records}
    normalized = {text: vector / np.linalg.norm(vector) for text, vector in vectors.items()}
    matrix = np.asarray([normalized[entry["text"]] for entry in cache])
    all_similarities = np.asarray([normalized[item["query"]] for item in items]) @ matrix.T
    rows = []
    for item, similarities in zip(items, all_similarities, strict=True):
        query = normalized[item["query"]]
        winner = int(np.argmax(similarities))  # Cache IDs already ascending; first wins an exact tie.
        entry = cache[winner]
        rows.append({
            "id": item["id"], "group": item["type"], "family": item["family"],
            "pair_cosine": float(np.clip(normalized[item["source"]] @ query, -1, 1)),
            "pair_correct": item["label"] == "same",
            "pair_guard": guard_passes(item["source"], item["query"]),
            "winner": entry["id"], "lookup_cosine": float(np.clip(similarities[winner], -1, 1)),
            "lookup_correct": entry["id"] in item["acceptable_ids"],
            "lookup_guard": guard_passes(entry["text"], item["query"]),
        })
    sweep = []
    for threshold in THRESHOLDS:
        result = {"threshold": threshold}
        for mode in ("pair", "lookup"):
            for guarded in (False, True):
                arm = mode + ("_guarded" if guarded else "")
                groups = {}
                for group in sorted({row["group"] for row in rows} | {"all", "near_miss"}):
                    cohort = [row for row in rows if group == "all" or row["group"] == group or
                              (group == "near_miss" and row["group"] not in ("paraphrase", "unrelated"))]
                    served = [row for row in cohort if row[f"{mode}_cosine"] >= threshold and
                              (not guarded or row[f"{mode}_guard"])]
                    groups[group] = {
                        "denominator": len(cohort), "served": len(served),
                        "useful": sum(row[f"{mode}_correct"] for row in served),
                        "wrong": sum(not row[f"{mode}_correct"] for row in served),
                        "abstained": len(cohort) - len(served),
                    }
                result[arm] = groups
        sweep.append(result)
        result["guard_effect"] = {
            mode: {group: {
                "wrong_removed": result[mode][group]["wrong"] - result[mode + "_guarded"][group]["wrong"],
                "useful_lost": result[mode][group]["useful"] - result[mode + "_guarded"][group]["useful"],
                "denominator": result[mode][group]["denominator"],
            } for group in result[mode]} for mode in ("pair", "lookup")
        }
    safe = next((entry for entry in sweep if entry["pair"]["near_miss"]["wrong"] <= 2), None)
    query_texts = {item["query"] for item in items}
    times = [row["milliseconds"] for row in records if row["text"] in query_texts and row["attempts"] == 1]
    return {
        "model": model, "status": "fixture_only" if dry_run else "measured",
        "manifest": str(root.relative_to(HERE)).replace("\\", "/") + "/manifest.json",
        "distinct_pairs": len(rows), "rows": rows, "sweep": sweep,
        "safe_threshold": None if safe is None else safe["threshold"],
        "latency": {"distinct_queries": len(times), "median_ms": float(np.median(times)) if times else None,
                    "p95_ms": float(np.quantile(times, 0.95)) if times else None,
                    "retried_queries": sum(row["text"] in query_texts and row["attempts"] > 1 for row in records),
                    "scope": "single successful attempts; resumed vectors retain original measurement"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["local", "api"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run:
        check()
    models = ["fixture"] if args.dry_run else args.models
    output = (HERE / "development/full-fixture" / digest(HERE / "cache.jsonl")[:12] / "analysis"
              if args.dry_run else HERE / "analysis")
    results = {model: score(model, args.dry_run) for model in models}
    for model, result in results.items():
        atomic_json(output / f"{model}.json", result)
    atomic_json(output / "figures-data/threshold-sweep.json",
                {model: result["sweep"] for model, result in results.items()})
    at_safe = {}
    for model, result in results.items():
        at_safe[model] = next((entry for entry in result["sweep"]
                              if entry["threshold"] == result["safe_threshold"]), None)
    atomic_json(output / "figures-data/wrong-hits-by-type.json", at_safe)
    atomic_json(output / "figures-data/guard-before-after.json", at_safe)
    # This handover is generated solely from saved measurements.
    lines = ["# Measured results" if not args.dry_run else "# Offline fixture report",
             "", "Counts refer to distinct pairs. Cache results refer to distinct lookups.", ""]
    for model in results:
        safe = at_safe[model]
        lines.append(f"## {model}")
        lines.append("")
        if safe is None:
            lines.append("No tested threshold meets the observed near-miss error budget.")
        else:
            wrong = safe["pair"]["near_miss"]["wrong"]
            useful = safe["pair"]["paraphrase"]["useful"]
            lines.append(f"Threshold {safe['threshold']:.2f} admits {wrong} of 180 near-misses "
                         f"and {useful} of 120 paraphrases.")
            lookup = safe["lookup"]["all"]
            effect = safe["guard_effect"]["pair"]
            lines.append(f"The cache serves {lookup['wrong']} wrong and {lookup['useful']} useful answers "
                         f"out of {lookup['denominator']} lookups at that threshold.")
            lines.append(f"The guard removes {effect['near_miss']['wrong_removed']} wrong hits out of "
                         f"180 near-miss pairs and costs {effect['paraphrase']['useful_lost']} useful hits "
                         "out of 120 paraphrase pairs.")
            lines.append(f"Sources {model}.json, sweep[].lookup.all and sweep[].guard_effect.pair.")
        lines.append(f"Source {model}.json, safe_threshold and sweep[].pair fields.")
        latency = results[model]["latency"]
        lines.append(f"Embedding latency is median {latency['median_ms']} ms and p95 {latency['p95_ms']} ms "
                     f"over {latency['distinct_queries']} successful first-attempt queries. "
                     f"Source {model}.json, latency fields.")
        lines.append("")
    lines += ["## Limits", "", "The synthetic cohort has 30 near-miss families with six contextual variants each.",
              "The 120 paraphrases use ten fact families. The 760 cache distractors use twenty frames.",
              "These counts describe this cohort and its traffic mix. Conditional bootstrap intervals cannot "
              "establish a population error ceiling.", ""]
    output.mkdir(parents=True, exist_ok=True)
    (output / "FULL-RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "RESULTS.md").write_text(
        "# Claim sources\n\nThresholds and counts come from each model JSON's safe_threshold and sweep fields.\n"
        "Individual outcomes come from rows, keyed by item ID. Query and answer text lives in items.jsonl.\n"
        "Latency comes from latency and the source run's embeddings.json milliseconds field.\n",
        encoding="utf-8",
    )
    api = results.get("api")
    candidates = [] if api is None else sorted(
        [row for row in api["rows"] if row["group"] not in ("paraphrase", "unrelated")
         and row["pair_cosine"] >= 0.8], key=lambda row: (-row["pair_cosine"], row["id"]))
    example = dict(candidates[0], served_at_threshold=0.80) if candidates else None
    atomic_json(output / "opening-example.json", example)
    (output / "HANDOVER-FOR-POST.md").write_text(
        "\n".join(lines) + "\nOpening example follows opening-example.json and items.jsonl. "
        + ("The API run is pending, so opening-example selection is pending.\n" if api is None else
           "A null example means no near-miss passed the preregistered example rule.\n") +
        "Read uncertainty.json before comparing models. Avoid production-frequency, universal safety "
        "and realised cost-saving claims.\n", encoding="utf-8")
    print(f"Scored {len(results)} model(s) into {output}.")


if __name__ == "__main__":
    main()
