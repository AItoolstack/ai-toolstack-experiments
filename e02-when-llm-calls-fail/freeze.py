"""Pin a review snapshot; verify it; or record the user's explicit approval of that snapshot."""

import argparse
import json
from datetime import datetime, timezone

from e2core import ROOT, digest, input_hashes, sha, write_json

REVIEW_FILES = [
    "DESIGN.md",
    "config.json",
    "e2core.py",
    "engine.py",
    "build_items.py",
    "run.py",
    "analyse.py",
    "analysis_e2.py",
    "freeze.py",
    "test_e02.py",
    "pilot_fixtures.py",
    "README.md",
    "REVIEW-CHECKLIST.md",
    "run-pilot.ps1",
    "requirements-dev.txt",
    ".gitignore",
    ".gitattributes",
    "items.jsonl",
    "INPUT-HEALTH.json",
    "figures-post/make_figures.py",
]


def snapshot():
    return {
        "schema": 1,
        "status": "REVIEW_SNAPSHOT_NOT_EVALUATION_APPROVAL",
        "date": "2026-11-01",
        "source_sha256": {name: sha(ROOT / name) for name in REVIEW_FILES},
        "e06_input_sha256": input_hashes(),
    }


def check():
    saved = json.loads((ROOT / "FREEZE.json").read_text(encoding="utf-8"))
    current = snapshot()
    if saved != current:
        changed = [
            name for name, value in current["source_sha256"].items() if saved["source_sha256"].get(name) != value
        ]
        changed += [
            "E06/" + name
            for name, value in current["e06_input_sha256"].items()
            if saved["e06_input_sha256"].get(name) != value
        ]
        raise ValueError("Review freeze mismatch; investigate changed code/data: " + ", ".join(changed))
    return digest(saved)


def require_approval():
    review = check()
    path = ROOT / "APPROVAL.json"
    if not path.exists():
        raise ValueError("Full evaluation blocked: Tej must review DESIGN.md and the pilot first. No APPROVAL.json.")
    approval = json.loads(path.read_text(encoding="utf-8"))
    if approval.get("review_sha256") != review or not approval.get("approved_by") or not approval.get("note"):
        raise ValueError("Approval does not bind to this exact review snapshot")
    return review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--approve", action="store_true", help="User only: record actual design/pilot approval")
    parser.add_argument("--approved-by")
    parser.add_argument("--note")
    args = parser.parse_args()
    if args.write:
        path = ROOT / "FREEZE.json"
        if path.exists():
            raise SystemExit("Review snapshot exists. Archive it before an explicitly documented revision.")
        write_json(path, snapshot())
        print("Wrote review snapshot. This is NOT approval for a full evaluation.")
    elif args.approve:
        review = check()
        if not args.approved_by or not args.note:
            parser.error("--approve requires --approved-by and --note recording actual approval")
        path = ROOT / "APPROVAL.json"
        if path.exists():
            raise SystemExit("Approval already exists; never overwrite approval history")
        write_json(
            path,
            {
                "review_sha256": review,
                "approved_by": args.approved_by,
                "note": args.note,
                "recorded_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        print("Recorded approval of this exact snapshot. Full offline evaluation can now run.")
    else:
        print("Review snapshot verified: " + check())


if __name__ == "__main__":
    main()
