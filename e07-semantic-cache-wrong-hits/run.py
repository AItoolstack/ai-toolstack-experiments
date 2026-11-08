"""Offline wiring check for the first E7 review milestone."""
import argparse
import hashlib
import json
import math
import re

from build_items import HERE, validate


def fixture_vector(text):
    """Hashed word counts exercise cosine plumbing; they provide no model evidence."""
    vector = [0.0] * 128
    for word in re.findall(r"\w+", text.casefold()):
        bucket = int(hashlib.sha256(word.encode()).hexdigest()[:8], 16) % len(vector)
        vector[bucket] += 1
    return vector


def cosine(left, right):
    if len(left) != len(right) or not left:
        raise ValueError("Vector dimensions must match and be nonempty.")
    if not all(math.isfinite(value) for value in left + right):
        raise ValueError("Vectors must be finite.")
    denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    if denominator == 0:
        raise ValueError("Zero vectors cannot be scored.")
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right)) / denominator))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Run offline fixture vectors.")
    args = parser.parse_args()
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
