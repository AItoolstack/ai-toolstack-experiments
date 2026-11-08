"""Freeze the audited protocol and detect changed inputs before any real run."""
import argparse
import importlib.metadata
import json
import re

from common import HERE, MODELS, THRESHOLDS, atomic_json, digest, read_jsonl
from corpus import validate_full


def inputs():
    patterns = ("*.py", "requirements.txt", "DESIGN.md", "items.jsonl", "cache.jsonl", "development/AUDIT.md",
                "development/*audit*.jsonl", "development/blind-*.jsonl",
                "development/sample_pairs.tsv")
    return sorted({path for pattern in patterns for path in HERE.glob(pattern)})


def check():
    path = HERE / "FREEZE.json"
    if not path.exists():
        raise ValueError("No freeze exists. Complete the audit and create it before running real models.")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    actual = {str(path.relative_to(HERE)).replace("\\", "/"): digest(path) for path in inputs()}
    if actual != frozen["sha256"]:
        raise ValueError("Frozen inputs changed. Restore them or record a pre-run amendment and freeze again.")
    return frozen


def create(revision):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Supply an immutable 40-character local model revision.")
    items = read_jsonl(HERE / "items.jsonl")
    validate_full(items)
    key = read_jsonl(HERE / "development/audit-key.jsonl")
    responses = read_jsonl(HERE / "development/blind-responses.jsonl")
    judged = {row["id"]: row for row in responses}
    if len(key) < 60 or len(judged) != len(responses) or set(judged) != {row["id"] for row in key}:
        raise ValueError("Blind audit is incomplete or duplicated.")
    disagreements = [row["id"] for row in key if judged[row["id"]]["label"] != row["expected"]]
    if disagreements:
        raise ValueError(f"Resolve and re-audit disagreements before freezing: {disagreements}")
    versions = {}
    for package in ("numpy", "sentence-transformers", "torch", "transformers", "threadpoolctl",
                    "tokenizers", "huggingface-hub", "scipy", "scikit-learn", "safetensors"):
        versions[package] = importlib.metadata.version(package)
    models = {name: dict(spec) for name, spec in MODELS.items() if name != "fixture"}
    models["local"]["revision"] = revision
    models["local"].update(device="cpu", torch_threads=1)
    models["api"]["revision"] = "hosted-alias-no-immutable-revision"
    atomic_json(HERE / "FREEZE.json", {
        "schema": 1, "date": "2026-11-08", "models": models, "packages": versions,
        "thresholds": THRESHOLDS, "safe_wrong_max": 2, "safe_denominator": 180,
        "bootstrap_replicates": 10000, "bootstrap_seed": 7007,
        "sha256": {str(path.relative_to(HERE)).replace("\\", "/"): digest(path) for path in inputs()},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--revision", help="Immutable local model weights commit.")
    args = parser.parse_args()
    try:
        if args.check:
            check()
        elif args.revision:
            create(args.revision)
            check()
        else:
            parser.error("Supply --check or --revision.")
    except (ValueError, importlib.metadata.PackageNotFoundError) as error:
        raise SystemExit(str(error)) from None
    print("Freeze check passed.")


if __name__ == "__main__":
    main()
