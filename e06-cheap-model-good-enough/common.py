"""Shared helpers for E06: models, prices, prompts, items and results files."""

from __future__ import annotations

import json
from pathlib import Path

from build_items import INVOICE_FIELDS, RAIL_POLICY, RULES_QUESTION, TOOL_SYSTEM

HERE = Path(__file__).resolve().parent
REPEATS = 3

# Short name -> how to call it, in price order. "reasoning": send reasoning effort.
# gpt-oss models go through OpenRouter pinned to Groq, as in E01, so both sizes share one host.
# GLM-5.3-Flash is pinned to Z.ai (its maker) because cheaper hosts don't state their quantisation.
# "repeats": calls per item (default REPEATS). Sol runs once: it is the top rung and the cascade
# fallback, and E01 already covered run-to-run consistency (decided 26 Oct).
# "control": a side measurement, left out of the cascades. glm-flash-t0 is the same model at
# temperature 0, to show how much of the cheap model's variation comes from sampling.
MODELS = {
    "oss-20b": {"provider": "openrouter", "model": "openai/gpt-oss-20b", "route": "groq", "reasoning": True},
    "luna": {"provider": "openai", "model": "gpt-6-luna", "route": None, "reasoning": True},
    "glm-flash": {"provider": "openrouter", "model": "z-ai/glm-5.3-flash", "route": "z-ai", "reasoning": True},
    "oss-120b": {"provider": "openrouter", "model": "openai/gpt-oss-120b", "route": "groq", "reasoning": True},
    "sol": {"provider": "openai", "model": "gpt-6.1-sol", "route": None, "reasoning": True, "repeats": 1},
    "glm-flash-t0": {
        "provider": "openrouter",
        "model": "z-ai/glm-5.3-flash",
        "route": "z-ai",
        "reasoning": True,
        "temperature": 0,
        "repeats": 1,
        "control": True,
    },
}
REASONING_EFFORT = "low"

# USD per million tokens (input, output), list prices for the host used. Reasoning tokens bill as output.
PRICES_CHECKED = "2026-10-26"
PRICES = {
    "oss-20b": (0.075, 0.30),  # Groq via OpenRouter (checked 25 Oct)
    "luna": (0.10, 0.50),  # OpenAI
    "glm-flash": (0.15, 0.50),  # Z.ai via OpenRouter (checked 26 Oct)
    "oss-120b": (0.15, 0.60),  # Groq via OpenRouter (checked 25 Oct)
    "sol": (2.00, 10.00),  # OpenAI
    "glm-flash-t0": (0.15, 0.50),
}


def repeats_for(name: str) -> int:
    return MODELS[name].get("repeats", REPEATS)


INVOICE_SYSTEM = (
    "Extract these fields from the invoice or credit note and reply with JSON only, using exactly these keys:\n"
    + "\n".join(
        [
            "supplier_name: the business that issued the document",
            "invoice_number: the document's own number",
            "invoice_date: YYYY-MM-DD",
            "due_date: YYYY-MM-DD, or null if the document gives no due date or terms",
            "currency: ISO 4217 code",
            "net_total: total before tax, as a number",
            "tax_total: total tax, as a number",
            "gross_total: total including tax, as a number",
            "amount_due: what the customer still has to pay now, as a number",
            "is_credit_note: true or false",
        ]
    )
    + "\nFor a credit note, give every amount as a negative number, and amount_due equals gross_total. "
    "Use null for any field the document does not give. Do not guess."
)
assert all(f in INVOICE_SYSTEM for f in INVOICE_FIELDS)

RULES_SYSTEM = (
    "You apply a company policy to a customer's case. Read the policy carefully and follow it exactly.\n"
    'Reply with JSON only: {"amount": <number, in pounds>, "rules_used": "<rule numbers, e.g. 2, 5>"}'
)


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_items(items_file: str) -> dict[str, dict]:
    return {item["id"]: item for item in read_jsonl(HERE / items_file)}


def load_tools() -> list[dict]:
    return json.loads((HERE / "tools.json").read_text(encoding="utf-8"))


def messages_for(item: dict) -> list[dict]:
    """System + user messages for one item. The same text for every model."""
    if item["task"] == "invoice":
        return [{"role": "system", "content": INVOICE_SYSTEM}, {"role": "user", "content": item["document"]}]
    if item["task"] == "tool":
        return [{"role": "system", "content": TOOL_SYSTEM}, {"role": "user", "content": item["request"]}]
    if item["task"] == "rules":
        user = f"Policy:\n{RAIL_POLICY}\n\nCase: {item['case']}\n\n{RULES_QUESTION}"
        return [{"role": "system", "content": RULES_SYSTEM}, {"role": "user", "content": user}]
    raise ValueError(item["task"])


def results_dir(items_file: str, dry_run: bool = False) -> Path:
    suffix = Path(items_file).stem.replace("items", "")
    return HERE / (("results-dry" if dry_run else "results") + suffix)


def load_runs(items_file: str, dry_run: bool = False) -> dict[str, list[dict]]:
    """Results keyed by model short name."""
    runs = {}
    for path in sorted(results_dir(items_file, dry_run).glob("*.jsonl")):
        if path.stem not in MODELS:
            continue
        rows = [r for r in read_jsonl(path) if r["repeat"] < repeats_for(path.stem)]
        if rows:
            runs[path.stem] = rows
    return runs


def cost_usd(name: str, prompt_tokens: int, completion_tokens: int) -> float:
    p_in, p_out = PRICES[name]
    return (prompt_tokens * p_in + completion_tokens * p_out) / 1e6
