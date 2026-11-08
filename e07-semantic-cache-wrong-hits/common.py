"""Shared serialization, guard and embedding-vector checks."""
import hashlib
import json
import math
import os
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
THRESHOLDS = [value / 100 for value in range(80, 100)]
MODELS = {
    "local": {"name": "sentence-transformers/all-MiniLM-L6-v2", "dimensions": 384},
    "api": {"name": "text-embedding-3-small", "dimensions": 1536},
    "fixture": {"name": "offline-hashed-words", "dimensions": 128},
}
# Date alternatives precede identifiers and numbers so each literal is counted once.
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
LITERALS = re.compile(
    rf"\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b|"
    rf"\b\d{{1,2}}\s+(?:{MONTHS})(?:\s+\d{{4}})?\b|"
    r"\b(?=[\w-]*[a-z])(?=[\w-]*\d)[\w]+(?:-[\w]+)*\b|"
    r"(?<!\w)[+-]?\d+(?:\.\d+)?|\b(?:no|not|never|neither|nor|without|cannot)\b|\b\w+n't\b",
    re.IGNORECASE,
)


def guard_tokens(text):
    return Counter(LITERALS.findall(text.lower().replace("’", "'")))


def guard_passes(left, right):
    return guard_tokens(left) == guard_tokens(right)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def validate_vector(vector, dimensions):
    if len(vector) != dimensions or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in vector):
        raise ValueError("Embedding has invalid dimensions or nonfinite values.")
    if not sum(x * x for x in vector):
        raise ValueError("Embedding has zero magnitude.")


def cosine(left, right):
    validate_vector(left, len(right))
    validate_vector(right, len(left))
    scale = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True)) / scale))
