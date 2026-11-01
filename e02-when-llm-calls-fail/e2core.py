"""Pinned E06 inputs and key-free E02 failure detection. No network or credentials."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
E06 = ROOT.parent / "e06-cheap-model-good-enough"
# E06 imports siblings by their historical names. Scope that search path so E06's
# run.py/freeze.py cannot shadow E02's commands. Load its scorer under a distinct name.
_old_path = sys.path[:]
_old_modules = set(sys.modules)
try:
    sys.path.insert(0, str(E06))
    _spec = importlib.util.spec_from_file_location("_e02_e06_scoring", E06 / "analyse.py")
    legacy = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(legacy)
    historical = sys.modules["common"]
finally:
    sys.path[:] = _old_path
    for _name in set(sys.modules) - _old_modules:
        _file = getattr(sys.modules[_name], "__file__", None)
        if _file and Path(_file).resolve().parent == E06:
            del sys.modules[_name]

INPUT_FILES = [
    "FREEZE.json",
    "items.jsonl",
    "items_samples.jsonl",
    "dataset-manifest.json",
    "tools.json",
    "policies.py",
    "analyse.py",
    "common.py",
    "build_items.py",
    "evaluation_items.py",
    "AUDIT-2026-10-29.md",
    "FULL-RUN-HEALTH-2026-10-29.md",
    "audit-review-2026-10-29/audit-resolution.json",
    "chart-assets/InterVariable.ttf",
    "chart-assets/Inter-LICENSE.txt",
] + [f"results_frozen_20261029/{name}.jsonl" for name in historical.STUDY_MODELS]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def read_jsonl(path: Path) -> list[dict]:
    # Blank lines are forbidden: source line references must remain exact.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def input_hashes() -> dict:
    return {name: sha(E06 / name) for name in INPUT_FILES}


def finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def detect(task: str, row: dict) -> str | None:
    """Observable response checks only. Never inspect gold or source task text."""
    if row.get("finish_reason") == "length":
        return "cutoff"
    if row.get("finish_reason") in {"content_filter", "incomplete"}:
        return "incomplete"
    if not row.get("content", "").strip() and not row.get("tool_calls"):
        return "empty"
    if task == "tool":
        name, args, how = legacy.tool_call_of(row)
        if how == "no_call":
            return None
        if how != "ok":
            return how
        if name not in legacy.TOOL_SPECS or not legacy.schema_valid(args, legacy.TOOL_SPECS[name]):
            return "invalid_tool_schema"
        return None
    parsed = legacy.parse_json(row.get("content", ""))
    if parsed is None:
        return "malformed_json"
    if task == "rules":
        return None if finite_number(parsed.get("amount")) else "invalid_amount"
    if task != "invoice":
        raise ValueError("Unknown task: " + task)
    if set(legacy.INVOICE_FIELDS) - set(parsed):
        return "missing_invoice_fields"
    for key in ("net_total", "tax_total", "gross_total", "amount_due"):
        if parsed[key] is not None and not finite_number(parsed[key]):
            return "invalid_invoice_type"
    for key in ("supplier_name", "invoice_number", "invoice_date", "due_date", "currency"):
        if parsed[key] is not None and not isinstance(parsed[key], str):
            return "invalid_invoice_type"
    if not isinstance(parsed["is_credit_note"], bool):
        return "invalid_invoice_type"
    return None


def default_response(task: str, variant: str) -> dict:
    if variant not in {"zero_numeric", "all_null"}:
        raise ValueError(variant)
    if task == "tool":
        return {"content": "No action selected.", "tool_calls": [], "finish_reason": "stop"}
    if task == "rules":
        payload = {"amount": 0, "rules_used": ""}
    elif task == "invoice":
        payload = dict.fromkeys(legacy.INVOICE_FIELDS)
        if variant == "zero_numeric":
            payload.update(dict.fromkeys(("net_total", "tax_total", "gross_total", "amount_due"), 0))
        payload["is_credit_note"] = False
    else:
        raise ValueError(task)
    return {"content": canonical(payload), "tool_calls": [], "finish_reason": "stop"}


@dataclass
class Inputs:
    items: dict
    cohorts: dict
    runs: dict
    refs: dict
    hashes: dict
    health: dict


def load_inputs() -> Inputs:
    rows = read_jsonl(E06 / "items.jsonl")
    items = {r["id"]: r for r in rows}
    if len(rows) != 102 or len(items) != 102:
        raise ValueError("Expected 102 unique E06 items")
    if Counter(r["task"] for r in rows) != {"invoice": 36, "tool": 36, "rules": 30}:
        raise ValueError("Unexpected E06 task coverage")
    manifest = json.loads((E06 / "dataset-manifest.json").read_text(encoding="utf-8"))
    cohorts = {"heldout": manifest["held_out_ids"], "development": manifest["development_ids"]}
    a, b = map(set, cohorts.values())
    if len(a) != 81 or len(b) != 21 or a & b or a | b != set(items):
        raise ValueError("Invalid E06 cohort partition")
    if any(len(set(v)) != len(v) for v in cohorts.values()):
        raise ValueError("Duplicate cohort item")
    runs, refs, health = {}, {}, {}
    for model in historical.STUDY_MODELS:
        rel = f"results_frozen_20261029/{model}.jsonl"
        answers = read_jsonl(E06 / rel)
        indexed = {(r["item"], r["repeat"]): r for r in answers}
        expected = {(ident, rep) for ident in items for rep in range(historical.MODEL_REPEATS[model])}
        if len(answers) != len(expected) or set(indexed) != expected:
            raise ValueError("Incomplete or duplicate saved response coverage: " + model)
        for line, row in enumerate(answers, 1):
            if row["model"] != model or row["task"] != items[row["item"]]["task"]:
                raise ValueError("Saved identity mismatch")
            for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
                if not isinstance(row[key], int) or row[key] < 0:
                    raise ValueError("Invalid token count")
            if not finite_number(row["latency_s"]) or row["latency_s"] < 0 or row["attempts"] != 1:
                raise ValueError("Invalid saved attempt/timing")
            refs[model, row["item"], row["repeat"]] = {"file": f"../e06-cheap-model-good-enough/{rel}", "line": line}
        runs[model] = indexed
        health[model] = {
            "rows": len(answers),
            "observable_faults": dict(
                Counter(reason for row in answers if (reason := detect(row["task"], row)) is not None)
            ),
        }
    if sum(v["rows"] for v in health.values()) != 1428:
        raise ValueError("Expected all 1,428 historical answers")
    cfg = config()
    if not set(cfg["pilot_ids"]) <= b or len(cfg["pilot_ids"]) != 10:
        raise ValueError("Pilot must use ten distinct development items")
    if len(set(cfg["pilot_ids"])) != 10:
        raise ValueError("Duplicate pilot ID")
    for ident in items:
        for track in cfg["primary_tracks"]:
            if (ident, track) not in runs[cfg["primary"]]:
                raise ValueError("Primary replay track missing")
        if (ident, 0) not in runs[cfg["fallback"]]:
            raise ValueError("Fallback answer missing")
    return Inputs(items, cohorts, runs, refs, input_hashes(), health)


def item_index(data: Inputs) -> list[dict]:
    return [
        {
            "id": ident,
            "task": data.items[ident]["task"],
            "cohort": cohort,
            "source": "../e06-cheap-model-good-enough/items.jsonl",
            "line": list(data.items).index(ident) + 1,
        }
        for cohort, ids in data.cohorts.items()
        for ident in sorted(ids)
    ]
