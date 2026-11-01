"""Scripted development diagnostics, excluded from all statistical results. No seed selection."""

import argparse
import gzip
import json
from pathlib import Path

from analysis_e2 import outcome
from e2core import ROOT, canonical, config, load_inputs, sha, write_json
from engine import response_for, simulate
from freeze import check

FIXTURES = ("first_primary_only", "all_primary", "all_calls")


def fixture_schedule(scenario, seed, ident, track, role, attempt):
    fixture = scenario["id"]
    if fixture == "first_primary_only":
        return role == "primary" and attempt == 0
    if fixture == "all_primary":
        return role == "primary"
    if fixture == "all_calls":
        return True
    raise ValueError(fixture)


def diagnostic_rows(data, cfg):
    for fixture in FIXTURES:
        for kind in cfg["failure_types"]:
            for ident in cfg["pilot_ids"]:
                task = data.items[ident]["task"]
                p = data.runs[cfg["primary"]][ident, 0]
                f = data.runs[cfg["fallback"]][ident, 0]
                refs = (data.refs[cfg["primary"], ident, 0], data.refs[cfg["fallback"], ident, 0])
                for design in cfg["designs"]:
                    yield simulate(
                        task,
                        ident,
                        0,
                        cfg["seeds"][0],
                        {"id": fixture, "failure": kind},
                        design,
                        "zero_numeric",
                        p,
                        f,
                        refs,
                        cfg,
                        injection_schedule=fixture_schedule,
                    )


def write_fixtures(out):
    review = check()
    data, cfg = load_inputs(), config()
    rows = list(diagnostic_rows(data, cfg))
    if len(rows) != 600:
        raise ValueError("Expected 3 scripts x 5 failure types x 10 development items x 4 policies")
    out.mkdir(parents=True, exist_ok=True)
    ledger = out / "scripted-ledger.jsonl.gz"
    with ledger.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        for row in rows:
            stream.write((canonical(row) + "\n").encode())
    examples = []
    for row in rows:
        # Fixed diagnostic example: first pilot ID, timeout, every script/policy.
        if row["item"] == cfg["pilot_ids"][0] and row["events"][0]["injected"] == "timeout":
            examples.append(
                {
                    "record": row,
                    "visible_response": {
                        k: response_for(row, data).get(k) for k in ("content", "tool_calls", "finish_reason")
                    },
                    "grade": outcome(row, data.items[row["item"]], response_for(row, data)),
                }
            )
    write_json(
        out / "example.json",
        {
            "status": "SCRIPTED_DEVELOPMENT_FIXTURE_NOT_STATISTICAL_EVIDENCE",
            "synthetic_task": data.items[cfg["pilot_ids"][0]],
            "examples": examples,
        },
    )
    lines = [
        "# Scripted failure diagnostics",
        "",
        "Development fixtures only. These scripts force failures; no probability or confidence claim is made.",
        "The unchanged probabilistic pilot happened to trigger zero failures. Its seed was not changed.",
        "These 600 separate records exercise three explicit schedules across all five failure types and ten",
        "development items. They never enter summary.json, uncertainty.json or publication results.",
        "",
        "The concrete example is fixed: inv01, timeout, primary track 0.",
        "Source references and visible outputs are in example.json.",
        "",
        "| Script | Design | Outcome | Calls | Modelled seconds |",
        "| --- | --- | --- | --- | --- |",
    ]
    for example in examples:
        row = example["record"]
        lines.append(
            f"| {row['scenario']} | {row['design']} | {example['grade']} | "
            f"{row['calls']} | {row['latency_seconds']:.2f} |"
        )
    lines += [
        "",
        "first_primary_only: initial primary call fails; all subsequent calls are healthy.",
        "all_primary: primary stays failed; fallback is healthy.",
        "all_calls: primary and fallback both stay failed.",
        "",
        "Healthy means no injected failure; the saved answer can still be wrong.",
        "",
    ]
    (out / "DIAGNOSTICS.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    write_json(
        out / "manifest.json",
        {
            "status": "SCRIPTED_DEVELOPMENT_ONLY",
            "rows": len(rows),
            "distinct_items": len(cfg["pilot_ids"]),
            "review_sha256": review,
            "input_sha256": data.hashes,
            "api_calls": 0,
            "outputs": {
                name: sha(out / name) for name in ("scripted-ledger.jsonl.gz", "example.json", "DIAGNOSTICS.md")
            },
        },
    )
    # Ensure gzip can be read back without truncation or serialization changes.
    with gzip.open(ledger, "rt", encoding="utf-8") as stream:
        if [json.loads(line) for line in stream] != rows:
            raise ValueError("Diagnostic ledger round trip failed")
    print("Verified 600 separate scripted diagnostic records; not statistical results; API calls: 0.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "development/scripted-diagnostics")
    args = parser.parse_args()
    write_fixtures(args.out)


if __name__ == "__main__":
    main()
