"""Resumable offline replay. --dry-run uses ten development items; no mode calls an API."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from e2core import ROOT, canonical, config, digest, load_inputs, sha, write_json
from engine import scenarios, simulate
from freeze import check, require_approval


def atomic_json(path, value):
    pending = path.with_suffix(".pending")
    write_json(pending, value)
    pending.replace(path)


def run_spec(data, cfg, dry_run, cohort, review):
    return {
        "schema": 1,
        "mode": "development_pilot" if dry_run else "approved_evaluation",
        "cohort": "development_pilot" if dry_run else cohort,
        "item_ids": cfg["pilot_ids"] if dry_run else sorted(data.cohorts[cohort]),
        "seeds": cfg["seeds"][:1] if dry_run else cfg["seeds"],
        "tracks": cfg["primary_tracks"][:1] if dry_run else cfg["primary_tracks"],
        "config": cfg,
        "config_sha256": digest(cfg),
        "review_sha256": review,
        "e06_input_sha256": data.hashes,
        "scenarios": list(scenarios(cfg)),
        "api_calls": 0,
        "time_and_cost": "MODELLED_PROXIES_NOT_OBSERVED_RECOVERY",
    }


def shard_records(spec, scenario, seed, data):
    cfg = spec["config"]
    for ident in spec["item_ids"]:
        task = data.items[ident]["task"]
        for track in spec["tracks"]:
            primary = data.runs[cfg["primary"]][ident, track]
            fallback = data.runs[cfg["fallback"]][ident, 0]
            refs = (data.refs[cfg["primary"], ident, track], data.refs[cfg["fallback"], ident, 0])
            for variant in cfg["default_variants"]:
                for design in cfg["designs"]:
                    yield simulate(task, ident, track, seed, scenario, design, variant, primary, fallback, refs, cfg)


def execute(out: Path, spec, data):
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "run.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != spec:
            raise ValueError("Resume refused: run specification, input hashes or review snapshot changed")
    else:
        if any(out.iterdir()):
            raise ValueError("New run directory must be empty")
        atomic_json(manifest_path, spec)
    progress_path = out / "progress.json"
    progress = (
        json.loads(progress_path.read_text(encoding="utf-8"))
        if progress_path.exists()
        else {"spec_sha256": digest(spec), "shards": {}}
    )
    if progress["spec_sha256"] != digest(spec):
        raise ValueError("Progress belongs to another run")
    expected_names = {f"{scenario['id']}--{seed}.jsonl.gz" for scenario in spec["scenarios"] for seed in spec["seeds"]}
    if set(progress["shards"]) - expected_names:
        raise ValueError("Unexpected shard in resume index")
    shards = out / "shards"
    shards.mkdir(exist_ok=True)
    expected_count = (
        len(spec["item_ids"])
        * len(spec["tracks"])
        * len(spec["config"]["designs"])
        * len(spec["config"]["default_variants"])
    )
    for scenario in spec["scenarios"]:
        for seed in spec["seeds"]:
            name = f"{scenario['id']}--{seed}.jsonl.gz"
            target = shards / name
            if name in progress["shards"]:
                entry = progress["shards"][name]
                if not target.exists() or sha(target) != entry["sha256"] or entry["rows"] != expected_count:
                    raise ValueError("Saved shard changed; resume refused: " + name)
                continue
            pending = target.with_suffix(".pending")
            count = 0
            with pending.open("wb") as raw:
                with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
                    for row in shard_records(spec, scenario, seed, data):
                        zipped.write((canonical(row) + "\n").encode())
                        count += 1
            if count != expected_count:
                raise ValueError("Incomplete shard")
            pending.replace(target)
            progress["shards"][name] = {"sha256": sha(target), "rows": count}
            atomic_json(progress_path, progress)
    print(
        f"Complete: {len(progress['shards'])} shards, "
        f"{sum(v['rows'] for v in progress['shards'].values())} paired replay records; API calls: 0."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--cohort", choices=["heldout", "development"], default="heldout")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    review = check() if args.dry_run else require_approval()
    data, cfg = load_inputs(), config()
    spec = run_spec(data, cfg, args.dry_run, args.cohort, review)
    out = args.out or (ROOT / "development/pilot-run" if args.dry_run else ROOT / "results" / args.cohort)
    execute(out.resolve(), spec, data)


if __name__ == "__main__":
    main()
