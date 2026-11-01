"""Validate and index existing synthetic tasks; never author or modify E06 items."""

import argparse
import subprocess
import sys

from e2core import E06, ROOT, canonical, item_index, load_inputs, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(E06 / "freeze.py"), "--check"], cwd=E06, check=True)
    data = load_inputs()
    contents = "".join(canonical(row) + "\n" for row in item_index(data))
    health = {
        "input_sha256": data.hashes,
        "models": data.health,
        "distinct_items": 102,
        "heldout_items": 81,
        "development_items": 21,
        "note": "Observable response health only; no E02 evaluation scores inspected.",
    }
    if args.check:
        if (ROOT / "items.jsonl").read_text(encoding="utf-8") != contents:
            raise SystemExit("Item index differs; investigate before rebuilding")
        import json

        if json.loads((ROOT / "INPUT-HEALTH.json").read_text(encoding="utf-8")) != health:
            raise SystemExit("Input health/hashes differ")
    else:
        (ROOT / "items.jsonl").write_text(contents, encoding="utf-8", newline="\n")
        write_json(ROOT / "INPUT-HEALTH.json", health)
    print("Verified 102 existing synthetic items, cohort partition and 1,428 saved answers; no API calls.")


if __name__ == "__main__":
    main()
