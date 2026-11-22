"""Chunkers. Each returns a list of (start_char, end_char) ranges over the contract text.

Sizes are in words (whitespace-separated). One English word is roughly 1.3 tokens.
"""
from __future__ import annotations

import re

from common import words_with_offsets

PARA_RE = re.compile(r"\n[ \t]*\n")


def fixed(text: str, size: int, overlap: int = 0) -> list[tuple[int, int]]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("need size > 0 and 0 <= overlap < size")
    w = words_with_offsets(text)
    step = size - overlap
    out = []
    i = 0
    while i < len(w):
        j = min(i + size, len(w))
        out.append((w[i][0], w[j - 1][1]))
        if j == len(w):
            break
        i += step
    return out


def paragraphs(text: str) -> list[tuple[int, int]]:
    """Blank-line separated blocks, as character ranges, skipping empty ones."""
    out, start = [], 0
    for m in PARA_RE.finditer(text):
        if text[start:m.start()].strip():
            out.append((start, m.start()))
        start = m.end()
    if text[start:].strip():
        out.append((start, len(text)))
    return out


def paragraph_aware(text: str, max_words: int) -> list[tuple[int, int]]:
    """Merge whole paragraphs up to max_words; split any paragraph longer than that with fixed windows."""
    out: list[tuple[int, int]] = []
    cur_s = cur_e = None
    cur_n = 0
    for s, e in paragraphs(text):
        n = len(text[s:e].split())
        if n > max_words:
            if cur_s is not None:
                out.append((cur_s, cur_e))
                cur_s, cur_n = None, 0
            sub = text[s:e]
            out.extend((s + a, s + b) for a, b in fixed(sub, max_words))
            continue
        if cur_s is not None and cur_n + n > max_words:
            out.append((cur_s, cur_e))
            cur_s, cur_n = None, 0
        if cur_s is None:
            cur_s = s
        cur_e, cur_n = e, cur_n + n
    if cur_s is not None:
        out.append((cur_s, cur_e))
    return out


def configs() -> dict[str, dict]:
    """Every chunking setting in the experiment, by name."""
    cfg = {}
    for size in (64, 128, 256, 512, 1024):
        cfg[f"fixed-{size}"] = {"kind": "fixed", "size": size, "overlap": 0}
        cfg[f"fixed-{size}-ov20"] = {"kind": "fixed", "size": size, "overlap": size // 5}
    for size in (256, 512):
        cfg[f"para-{size}"] = {"kind": "para", "size": size, "overlap": 0}
    return cfg


def chunk(text: str, cfg: dict) -> list[tuple[int, int]]:
    if cfg["kind"] == "fixed":
        return fixed(text, cfg["size"], cfg["overlap"])
    if cfg["kind"] == "para":
        return paragraph_aware(text, cfg["size"])
    raise ValueError(cfg)
