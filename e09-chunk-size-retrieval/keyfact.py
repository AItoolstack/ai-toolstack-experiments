"""Key-fact check for Governing Law: does the text passed to the model name the governing jurisdiction?

The strict score asks for a complete expert span. A chunk can cut the span and still carry the answer
("...laws of the State of Delaware without giving ||| effect to..."), or keep most of the span and lose it.
For Governing Law the answer is a place name, so it can be checked mechanically.
"""
from __future__ import annotations

import re

US_STATES = """Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia Hawaii Idaho
Illinois Indiana Iowa Kansas Kentucky Louisiana Maine Maryland Massachusetts Michigan Minnesota Mississippi Missouri
Montana Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania Tennessee Texas Utah Vermont Virginia Washington Wisconsin
Wyoming""".split()
MULTI = ["New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Rhode Island",
         "South Carolina", "South Dakota", "West Virginia", "District of Columbia", "England and Wales", "Hong Kong",
         "British Columbia", "Cayman Islands", "British Virgin Islands", "Republic of Korea", "People's Republic of China"]
OTHER = ["England", "Ontario", "Quebec", "Israel", "Germany", "France", "Switzerland", "Singapore", "Japan", "China",
         "Netherlands", "Ireland", "Sweden", "Canada", "Australia", "India", "Italy", "Spain", "Denmark", "Norway",
         "Finland", "Belgium", "Luxembourg", "Bermuda", "Taiwan", "Korea", "Scotland", "Alberta", "PRC", "English"]
NAMES = sorted(MULTI + US_STATES + OTHER, key=len, reverse=True)
NAME_RE = re.compile(r"\b(" + "|".join(re.escape(n) for n in NAMES) + r")\b", re.IGNORECASE)


def jurisdiction(span_text: str) -> str | None:
    """First place named in the expert span (the governing law is normally named first)."""
    m = NAME_RE.search(" ".join(span_text.split()))
    return m.group(1).lower() if m else None


def place_range(text: str, span: list[int]) -> tuple[int, int] | None:
    """Character range of the first place name inside an expert span."""
    m = NAME_RE.search(text, span[0], span[1])
    return (m.start(), m.end()) if m else None


def carries_place(top: list[tuple[int, int]], rng: tuple[int, int]) -> bool:
    """A passed chunk holds the place name taken from the clause itself (not from an address elsewhere)."""
    return any(c[0] <= rng[0] and rng[1] <= c[1] for c in top)
