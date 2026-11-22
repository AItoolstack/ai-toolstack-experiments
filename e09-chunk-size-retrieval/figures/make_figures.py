"""Post figures for E9 and E9b in the site's house style (style guide section 7, since 1 Nov 2026).

400-unit canvas, text 15+, rendered at 2.4x to 960 px PNG. Amber only where a model is involved,
red only for the failure. Numbers are read from ../analysis/*.json, not typed in.
Usage: python figures/make_figures.py  (needs cairosvg; Inter fonts installed)
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import cairosvg

HERE = Path(__file__).resolve().parent
AN = HERE.parent / "analysis"
D = "2026-11-22"
W, PAD = 400, 14
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
INK, MUTED, LINE, BAR = "#1F2328", "#4A4F57", "#C9C5BC", "#DDD9D0"
AMB_LINE, AMB_BG, AMB_TXT = "#B7791F", "#FDF6EA", "#7A5112"
RED_LINE, RED_BG, RED_TXT = "#C53030", "#FDECEC", "#9B2C2C"
CHAR_W = 0.53  # rough Inter width per font-size unit, for wrapping


def wrap(s: str, width: float, size: float) -> list[str]:
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if len(t) * size * CHAR_W <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


class Fig:
    def __init__(self, alt: str):
        self.alt, self.parts, self.y = alt, [], PAD

    def text(self, x, y, s, size=16, fill=INK, weight=400, anchor="start"):
        assert size >= 15
        self.parts.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
                          f'text-anchor="{anchor}">{escape(s)}</text>')

    def rect(self, x, y, w, h, fill="#FFFFFF", stroke=LINE, rx=8, width=1.5):
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="{width}"/>')

    def label(self, s, size=15, fill=MUTED, weight=600):
        for ln in wrap(s, W - 2 * PAD, size * 1.08 if weight >= 600 else size):
            self.y += size + 5
            self.text(PAD, self.y, ln, size, fill, weight)
        self.y += 8

    def box(self, body, head=None, fill="#FFFFFF", stroke=LINE, color=INK, size=16):
        lines = wrap(body, W - 2 * PAD - 28, size)
        h = 14 + (22 if head else 0) + len(lines) * (size + 6) + 10
        self.rect(PAD, self.y, W - 2 * PAD, h, fill, stroke)
        yy = self.y + 14
        if head:
            yy += 15
            self.text(PAD + 14, yy, head, 15, color, 700)
            yy += 7
        for ln in lines:
            yy += size + 6
            self.text(PAD + 14, yy - 4, ln, size, INK if color == INK else color)
        self.y += h + 10

    def bars(self, rows, total, best=None, unit=""):
        """rows: (label, value). Horizontal bars on one scale, value printed at the end."""
        x0, bw = PAD, W - 2 * PAD - 64
        for name, v in rows:
            bold = name == best
            self.y += 20
            self.text(x0, self.y, name, 15, INK, 700 if bold else 400)
            self.y += 6
            self.rect(x0, self.y, bw, 16, "#FFFFFF", LINE, rx=3, width=1)
            self.rect(x0, self.y, bw * v / total, 16, INK if bold else BAR, INK if bold else BAR, rx=3, width=1)
            self.text(x0 + bw + 8, self.y + 14, f"{v}{unit}", 16, INK, 700 if bold else 400)
            self.y += 22

    def note(self, s, size=15):
        for ln in wrap(s, W - 2 * PAD, size):
            self.y += size + 5
            self.text(PAD, self.y, ln, size, MUTED)
        self.y += 6

    def save(self, name: str) -> Path:
        h = int(self.y + PAD)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" font-family="{FONT}" '
               f'role="img" aria-label="{escape(self.alt)}"><rect width="{W}" height="{h}" fill="#FFFFFF"/>' + "".join(self.parts) + "</svg>")
        out = HERE / f"{name}-v1-{D}.png"
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=960)
        (HERE / f"{name}-v1-{D}.alt.txt").write_text(self.alt + "\n", encoding="utf-8")
        return out


def load(name):
    return json.loads((AN / name).read_text(encoding="utf-8"))


def e09_half_rule():
    ex = {e["item_id"]: e for e in load("examples.json")}["c43-04"]
    f = Fig(f"Question: can a party terminate without cause? Sent to the model, a 256-word chunk ending: {ex['received_with_fixed_256']} "
            f"Left in the previous chunk: {ex['not_received']}. Paragraph-aware chunks kept the clause whole.")
    f.label("Can a party terminate without cause, and with how much notice?", 15, INK, 700)
    f.box(ex["not_received"], "Start of the clause: left in another chunk", RED_BG, RED_LINE, RED_TXT)
    f.box(ex["received_with_fixed_256"], "Rest of the clause: sent to the model", AMB_BG, AMB_LINE, AMB_TXT)
    f.note("Fixed 256-word chunks, keyword search, 1,000 words. Paragraph-aware chunks kept the clause whole.")
    return f.save("e09-half-a-rule")


def e09_by_setting():
    b = load("bm25.json")
    names = [("Fixed 64 words", "fixed-64"), ("Fixed 128 words", "fixed-128"), ("Fixed 128, 20% overlap", "fixed-128-ov20"),
             ("Fixed 256 words", "fixed-256"), ("Fixed 512 words", "fixed-512"), ("Fixed 1,024 words", "fixed-1024"),
             ("Paragraphs, up to 256 words", "para-256")]
    rows = [(n, b[k]["budget"]["1000"]["counts"]["found"]) for n, k in names]
    f = Fig("Questions out of 334 where the complete clause reached the model, with 1,000 words passed: " +
            "; ".join(f"{n} {v}" for n, v in rows) + ".")
    f.label("Complete clause reached the model, out of 334", 15, MUTED, 600)
    f.bars(rows, 334, best="Paragraphs, up to 256 words")
    f.note("Keyword search. Each setting passed up to 1,000 words.")
    return f.save("e09-complete-clause-by-setting")


def e09_cut():
    bd = load("boundaries.json")
    names = [("Fixed 64 words", "fixed-64"), ("Fixed 128 words", "fixed-128"), ("Fixed 256 words", "fixed-256"),
             ("Fixed 512 words", "fixed-512"), ("Fixed 1,024 words", "fixed-1024"), ("Paragraphs, up to 256 words", "para-256")]
    rows = [(n, bd[k]["no_intact_answer"]) for n, k in names]
    f = Fig("Questions out of 334 where no single chunk held the whole clause, before any search: " +
            "; ".join(f"{n} {v}" for n, v in rows) + ".")
    f.label("No chunk held the whole clause, out of 334", 15, MUTED, 600)
    f.bars(rows, 334)
    f.note("Counted before any search runs: the cut alone.")
    return f.save("e09-clauses-cut-by-size")


def e09b_vocabulary():
    f = Fig("Question: is there a cap or limit on either party's liability? The clause: Company is not liable for incidental, special or "
            "consequential damages for any reason. The question's words cap, limit and liability never appear in it, so keyword search "
            "missed it. Added contract words: liability, limitation, exceed, aggregate, damages, consequential, limit, maximum.")
    f.label("Is there a cap or limit on either party's liability?", 15, INK, 700)
    f.box("Company is not liable for incidental, special or consequential damages for any reason …", "The clause, as written")
    f.box("cap, limit, liability: none of them is in the clause. Search ranked a warranty paragraph first.", "Plain question", RED_BG, RED_LINE, RED_TXT)
    f.box("+ liability limitation exceed aggregate damages consequential limit maximum", "Question with contract words added")
    f.note("“damages” and “consequential” now match, and the clause is passed to the model.")
    return f.save("e09b-vocabulary")


def e09b_methods():
    r = load("improve.json")["test"]
    names = [("Starting point", "baseline"), ("Section headers added", "headers"), ("Small-to-big", "small-to-big"),
             ("Contract words added", "expansion"), ("Small-to-big + words", "small-to-big+expansion")]
    rows = [(n, r[k]["1000"]["found"]) for n, k in names]
    q = r["baseline"]["1000"]["questions"]
    f = Fig(f"Held-back test questions, out of {q}, where the complete clause reached the model with 1,000 words passed: " +
            "; ".join(f"{n} {v}" for n, v in rows) + f". Whole contract: {r['whole contract']['1000']['found']}, at a median of "
            f"{r['whole contract']['1000']['median_words']:,} words.")
    f.label(f"Complete clause reached the model, of {q}", 15, MUTED, 600)
    f.bars(rows, q, best="Contract words added")
    f.note(f"40 contracts not used to choose methods. Keyword search, 1,000 words. The whole contract scores {q} of {q} but is "
           f"{r['whole contract']['1000']['median_words']:,} words.")
    return f.save("e09b-methods")


if __name__ == "__main__":
    for fn in (e09_half_rule, e09_by_setting, e09_cut, e09b_vocabulary, e09b_methods):
        print(fn())
