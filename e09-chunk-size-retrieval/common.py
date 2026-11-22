"""Shared helpers for E09. Standard library only."""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
ANALYSIS = HERE / "analysis"

WORD_RE = re.compile(r"\S+")
TOKEN_RE = re.compile(r"[a-z0-9]+")

# Fixed settings. Changing any of these changes every number in the write-up.
SEED = 9009
N_CONTRACTS = 60
MIN_WORDS = 3000
TOP_K = (1, 3, 5)
KEEP_RANKED = 40  # chunks kept per ranking, enough to fill the largest word budget
BUDGETS = (500, 1000, 2000)  # words passed to the model

# CUAD category -> the plain question a reader would type.
QUESTIONS = {
    "Governing Law": "Which country's or state's law governs this agreement?",
    "Expiration Date": "When does this agreement expire or its initial term end?",
    "Renewal Term": "Does this agreement renew automatically, and for how long?",
    "Notice Period To Terminate Renewal": "How much notice is needed to stop this agreement from renewing?",
    "Termination For Convenience": "Can a party terminate this agreement without cause, and with how much notice?",
    "Anti-Assignment": "Can a party assign or transfer this agreement, and is consent needed?",
    "Change Of Control": "What happens if a party is acquired or has a change of control?",
    "Cap On Liability": "Is there a cap or limit on either party's liability?",
    "Non-Compete": "Is either party restricted from competing with the other?",
    "Audit Rights": "Does either party have the right to audit the other's books or records?",
}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def words_with_offsets(text: str) -> list[tuple[int, int]]:
    """(start, end) character offsets of each whitespace-separated word."""
    return [(m.start(), m.end()) for m in WORD_RE.finditer(text)]


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())
