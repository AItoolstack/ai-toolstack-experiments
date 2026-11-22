"""How a retrieved list of chunks is scored against the gold answer spans."""
from __future__ import annotations


def contains(chunk: tuple[int, int], span: list[int]) -> bool:
    return chunk[0] <= span[0] and span[1] <= chunk[1]


def overlaps(chunk: tuple[int, int], span: list[int]) -> bool:
    return chunk[0] < span[1] and span[0] < chunk[1]


def intact_anywhere(chunks: list[tuple[int, int]], spans: list[list[int]]) -> bool:
    """Is at least one answer span complete inside some chunk of the document?"""
    return any(contains(c, s) for c in chunks for s in spans)


def covered(top: list[tuple[int, int]], span: list[int], text: str | None) -> bool:
    """Do the retrieved chunks together cover every word of the span? Gaps of whitespace between chunks are allowed."""
    pos = span[0]
    for s, e in sorted(top):
        if e <= pos:
            continue
        gap = text[pos:s] if (text is not None and s > pos) else ""
        if s > pos and gap.strip():
            return False
        if s > pos and text is None:
            return False
        pos = max(pos, e)
        if pos >= span[1]:
            return True
    return pos >= span[1] or (text is not None and not text[pos:span[1]].strip())


def outcome(top: list[tuple[int, int]], all_chunks: list[tuple[int, int]], spans: list[list[int]], text: str | None = None) -> str:
    """One label per question for a given list of retrieved chunks.

    found     the retrieved chunks hold a complete answer span (in one chunk, or split across retrieved neighbours)
    partial   retrieved chunks touch an answer but none holds a complete one
    cut       nothing retrieved touches an answer, and chunking left no complete answer anywhere
    missed    nothing retrieved touches an answer, though a complete one existed in some chunk
    """
    if any(contains(c, s) for c in top for s in spans) or any(covered(top, s, text) for s in spans):
        return "found"
    if any(overlaps(c, s) for c in top for s in spans):
        return "partial"
    return "missed" if intact_anywhere(all_chunks, spans) else "cut"
