"""Paired stratified bootstrap of saved item outcomes, with a family sensitivity arm."""
import argparse
import json

import numpy as np
from common import HERE, THRESHOLDS, atomic_json, digest
from freeze import check
from threadpoolctl import threadpool_limits


@threadpool_limits.wrap(limits=1, user_api="blas")
def bootstrap(results, repeats=10000, family=False):
    names = sorted(results)
    rows = results[names[0]]["rows"]
    ids = [row["id"] for row in rows]
    if any([row["id"] for row in results[name]["rows"]] != ids for name in names):
        raise ValueError("Models must contain the same ordered item cohort.")
    rng = np.random.default_rng(7007)
    weights = np.zeros((repeats, len(rows)), dtype=np.int16)
    for group in sorted({row["group"] for row in rows}):
        positions = [i for i, row in enumerate(rows) if row["group"] == group]
        units = sorted({rows[i]["family"] for i in positions}) if family else positions
        draws = rng.multinomial(len(units), np.full(len(units), 1 / len(units)), size=repeats)
        for j, unit in enumerate(units):
            for position in ([i for i in positions if rows[i]["family"] == unit] if family else [unit]):
                weights[:, position] = draws[:, j]
    output = {}
    for mode in ("pair", "lookup"):
        for guarded in (False, True):
            arm = mode + ("_guarded" if guarded else "")
            for group in sorted({row["group"] for row in rows} | {"all", "near_miss"}):
                eligible = np.asarray([group == "all" or row["group"] == group or
                                       (group == "near_miss" and row["group"] not in ("paraphrase", "unrelated"))
                                       for row in rows])
                for metric in ("useful", "wrong"):
                    samples = {}
                    for name in names:
                        model_rows = results[name]["rows"]
                        indicators = np.asarray([
                            [eligible[i] and row[f"{mode}_cosine"] >= threshold and
                             (not guarded or row[f"{mode}_guard"]) and
                             (row[f"{mode}_correct"] == (metric == "useful"))
                             for threshold in THRESHOLDS]
                            for i, row in enumerate(model_rows)], dtype=np.float64)
                        samples[name] = weights @ indicators
                    key = f"{arm}/{group}/{metric}"
                    output[key] = {
                        name: np.quantile(sample, [0.025, 0.975], axis=0).T.tolist()
                        for name, sample in samples.items()
                    }
                    for i, left in enumerate(names):
                        for right in names[i + 1:]:
                            output[key][f"{left}-minus-{right}"] = np.quantile(
                                samples[left] - samples[right], [0.025, 0.975], axis=0).T.tolist()
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["local", "api"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replicates", type=int, default=10000)
    args = parser.parse_args()
    if args.replicates < 1:
        parser.error("Replicates must be positive.")
    if not args.dry_run:
        check()
        if args.replicates != 10000:
            parser.error("The frozen analysis requires 10000 replicates.")
    root = (HERE / "development/full-fixture" / digest(HERE / "cache.jsonl")[:12] / "analysis"
            if args.dry_run else HERE / "analysis")
    names = ["fixture"] if args.dry_run else args.models
    results = {name: json.loads((root / f"{name}.json").read_text()) for name in names}
    atomic_json(root / "uncertainty.json", {
        "replicates": args.replicates, "seed": 7007, "thresholds": THRESHOLDS,
        "intervals": bootstrap(results, args.replicates),
        "family_sensitivity": bootstrap(results, args.replicates, family=True),
        "warning": "Selected-threshold intervals are conditional. Zero observed errors cannot bound unseen errors.",
    })
    print("Wrote paired item intervals, paired model differences and family sensitivity intervals.")


if __name__ == "__main__":
    main()
