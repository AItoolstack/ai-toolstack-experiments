"""Offline wiring check for the first E7 review milestone."""
import argparse
import hashlib
import json
import re

from build_items import HERE, validate
from common import cosine


def fixture_vector(text):
    """Hashed word counts exercise cosine plumbing; they provide no model evidence."""
    vector = [0.0] * 128
    for word in re.findall(r"\w+", text.casefold()):
        bucket = int(hashlib.sha256(word.encode()).hexdigest()[:8], 16) % len(vector)
        vector[bucket] += 1
    return vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Run offline fixture vectors.")
    parser.add_argument("--full", action="store_true", help="Run the full corpus.")
    parser.add_argument("--model", choices=("local", "api"), default="local")
    parser.add_argument("--estimate", action="store_true")
    args = parser.parse_args()
    if args.full or args.estimate:
        from runner import execute
        execute(args.model, args.dry_run, args.estimate)
        return
    if not args.dry_run:
        parser.error("This review milestone supports --dry-run only. Real runs follow design approval.")
    source = HERE / "items_samples.jsonl"
    items = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    validate(items)
    rows = [
        {"id": item["id"], "fixture_cosine": cosine(fixture_vector(item["source"]),
                                                  fixture_vector(item["query"]))}
        for item in items
    ]
    report = {
        "status": "offline_fixture_only",
        "warning": "Fixture scores exercise code paths and carry no embedding-model evidence.",
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "distinct_pairs": len(items),
        "rows": rows,
    }
    target = HERE / "development/dry-run.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Offline fixture completed for {len(rows)} distinct pairs. Report: {target}")


if __name__ == "__main__":
    main()
