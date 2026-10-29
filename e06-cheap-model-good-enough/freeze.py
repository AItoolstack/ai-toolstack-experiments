"""Record/check the local evaluation freeze. No network, credentials or inference."""

import argparse
import hashlib
import json
from pathlib import Path

from common import MODEL_REPEATS, MODELS, PRICES, REASONING_EFFORT, STUDY_MODELS, load_items, load_tools
from evaluation_items import build_all
from run import MAX_TOKENS, request_body

ROOT = Path(__file__).resolve().parent
FILES = [
    "../.gitattributes",
    "../pyproject.toml",
    "items.jsonl",
    "items_samples.jsonl",
    "tools.json",
    "dataset-manifest.json",
    "build_items.py",
    "evaluation_items.py",
    "policies.py",
    "common.py",
    "run.py",
    "analyse.py",
    "pilot_health.py",
    "freeze.py",
    "run-full.ps1",
    "audit-review-2026-10-29/audit-resolution.json",
    "blind-audit-2026-10-29/requests.jsonl",
    "blind-audit-2026-10-29/answers.jsonl",
    "blind-audit-2026-10-29/labels-review.jsonl",
    "blind-audit-2026-10-29/stage-one-lock.json",
    "blind-audit-2026-10-29/re-audit-requests.jsonl",
    "blind-audit-2026-10-29/re-audit-answers.jsonl",
    "blind-audit-2026-10-29/interpretation-review.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    items = load_items("items.jsonl")
    built, _ = build_all()
    if list(items.values()) != built:
        raise ValueError("Saved items differ from the validated generator")
    audit = json.loads((ROOT / "audit-review-2026-10-29/audit-resolution.json").read_text(encoding="utf-8"))
    if not audit["all_final_answers_match"]:
        raise ValueError("Audit disagreements remain")
    lock = json.loads((ROOT / "blind-audit-2026-10-29/stage-one-lock.json").read_text(encoding="utf-8"))
    if sha(ROOT / "blind-audit-2026-10-29/answers.jsonl") != lock["answers_sha256"]:
        raise ValueError("Original blind answers changed after labels were revealed")
    tools = load_tools()
    return {
        "freeze_date": "2026-10-29",
        "tag": "e06-frozen",
        "run_tag": "frozen_20261029",
        "status": "FROZEN_BEFORE_FULL_EVALUATION",
        "item_count": len(items),
        "development_items": 21,
        "held_out_items": 81,
        "study": {
            name: {
                "spec": MODELS[name],
                "repeats": MODEL_REPEATS[name],
                "price_per_million_input_output_usd": list(PRICES[name]),
                "reasoning_effort": REASONING_EFFORT,
                "max_output_tokens": MAX_TOKENS,
                "request_set_sha256": hashlib.sha256(
                    json.dumps(
                        [request_body(MODELS[name], item, tools) for item in items.values()], sort_keys=True
                    ).encode()
                ).hexdigest(),
            }
            for name in STUDY_MODELS
        },
        "source_sha256": {name: sha(ROOT / name) for name in FILES},
        "limits": [
            "Development items were seen in pilots; report held-out cohort separately.",
            "Validators were revised after development pilots; this is not a fully pre-pilot registration.",
            "The single Sol answer is reused; its variation is unmeasured.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "FREEZE.json"
    current = snapshot()
    if args.write:
        if path.exists():
            raise SystemExit("FREEZE.json already exists; do not replace a freeze")
        path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print("Wrote FREEZE.json. Commit the frozen sources and create the local e06-frozen tag.")
    else:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if current != saved:
            changed = [
                name for name, value in current["source_sha256"].items() if saved["source_sha256"].get(name) != value
            ]
            raise SystemExit("Freeze mismatch; do not run paid calls. Changed sources: " + ", ".join(changed))
        print("Freeze verified: 102 items; six model settings, prompts, tools, prices and audit hashes match.")


if __name__ == "__main__":
    main()
