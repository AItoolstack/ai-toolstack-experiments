"""Shared helpers for E01: items, results files, judge names and the label audit."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPEATS = 13

# "Clear" labels that did not survive the label audit (see README). They are left out of accuracy.
DISPUTED = {"s01", "s08", "f06"}

# Results file stem -> display name, for the four v2 judges.
JUDGES = {
    "openrouter-groq_openai-gpt-oss-120b__default": "gpt-oss-120b",
    "openrouter-groq_openai-gpt-oss-120b__temp0": "gpt-oss-120b, temp 0",
    "openai_gpt-6-luna__default": "GPT-6 Luna",
    "openai_gpt-6.1-sol__default": "GPT-6.1 Sol",
}

# USD per million tokens (input, output), list prices checked on PRICES_CHECKED.
# Reasoning tokens are billed as output.
PRICES_CHECKED = "2026-10-24"
PRICES = {
    "openai/gpt-oss-120b": (0.15, 0.60),  # Groq, paid tier
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6.1-sol": (2.00, 10.00),
}


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSON Lines file, skipping blank lines."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_items(items_file: str) -> dict[str, dict]:
    """Items keyed by id."""
    return {item["id"]: item for item in read_jsonl(HERE / items_file)}


def results_dir(items_file: str, dry_run: bool = False) -> Path:
    """items_v1.jsonl -> results_v1/, items_v2.jsonl -> results_v2/ (results-dry_* for dry runs)."""
    suffix = Path(items_file).stem.replace("items", "")
    return HERE / (("results-dry" if dry_run else "results") + suffix)


def task_of(item: dict) -> str:
    """v1 items have no task field: they are graded against a reference answer."""
    return item.get("task", "reference")


def load_runs(items_file: str, repeats: int | None = REPEATS, dry_run: bool = False) -> dict[str, list[dict]]:
    """Every results file for an item set, keyed by file stem, limited to the first `repeats` runs."""
    runs = {}
    for path in sorted(results_dir(items_file, dry_run).glob("*.jsonl")):
        rows = [r for r in read_jsonl(path) if repeats is None or r["repeat"] < repeats]
        if rows:
            runs[path.stem] = rows
    return runs
