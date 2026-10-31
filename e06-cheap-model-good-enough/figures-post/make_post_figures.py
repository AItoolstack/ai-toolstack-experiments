"""E06 post visuals (31 Oct 2026): mistakes caught and cost (the flow is in make_flow.py). 400-unit canvas shown at 480 px, min font 15.

Numbers come from analysis_frozen_20261029_heldout (summary-v2.json) and, for "caught", from the frozen
scorer applied to each cheap model's first answer (repeat 0): 20 wrong; the check caught 1, agreement 13.
Writes SVGs here; PNGs at 2x were rendered from them with Playwright and Inter (chart-assets)."""
from html import escape
from PIL import ImageFont
W, PAD = 400, 14
INK, MUTED, RULE, PAPER, ACC = "#1A1D24", "#4A5160", "#D9D6CF", "#FCFBF9", "#8F5A0E"
GREEN, GREEN_BG, GREY_BG, AMBER_BG, MISS = "#2D6B45", "#E7F2EA", "#F1EFEA", "#FAEEDD", "#E3D9D4"
_f = {}
def tw(s, size=16, bold=False):
    k = (size, bold)
    if k not in _f:
        f = ImageFont.truetype(str(__import__("pathlib").Path(__file__).resolve().parent.parent / "chart-assets" / "InterVariable.ttf"), size)
        try: f.set_variation_by_name("Bold" if bold else "Regular")
        except Exception: pass
        _f[k] = f
    return _f[k].getlength(s) * 1.04
def wrap(s, width, size=16, bold=False):
    lines, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w).strip()
        if tw(t, size, bold) <= width or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]
class Svg:
    def __init__(s): s.p = []; s.y = 0
    def text(s, x, y, t, size=16, fill=INK, bold=False, anchor="start"):
        assert size >= 15
        s.p.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{fill}" text-anchor="{anchor}">{escape(t)}</text>')
    def para(s, x, t, width, size=16, fill=INK, bold=False, lh=None):
        lh = lh or round(size * 1.35)
        for l in wrap(t, width, size, bold):
            s.y += lh; s.text(x, s.y - (lh - size) / 2 - 2, l, size, fill, bold)
    def rect(s, x, y, w, h, fill, stroke="none", rx=8, sw=1.5):
        s.p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def arrow(s, x, y1, y2):
        s.p.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2-7}" stroke="{MUTED}" stroke-width="1.6"/>'
                   f'<path d="M{x-5},{y2-8} L{x},{y2} L{x+5},{y2-8} Z" fill="{MUTED}"/>')
    def box(s, title, body, fill=GREY_BG, stroke=RULE, title_fill=INK, extra=None):
        top = s.y; s.y += 10
        if title: s.para(PAD + 12, title, W - 2 * PAD - 24, 16, title_fill, True)
        s.para(PAD + 12, body, W - 2 * PAD - 24, 15, MUTED if title else INK, False, 21)
        if extra: s.y += 4; s.para(PAD + 12, extra, W - 2 * PAD - 24, 15, GREEN, True, 21)
        s.y += 12
        s.p.insert(len(s.p) - 0, "")
        s.p.insert(s.mark, f'<rect x="{PAD}" y="{top:.1f}" width="{W-2*PAD}" height="{s.y-top:.1f}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    def begin_box(s): s.mark = len(s.p)
    def svg(s):
        h = round(s.y + PAD)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="480" height="{round(h*1.2)}" '
                f'font-family="Inter, \'Segoe UI\', system-ui, -apple-system, Helvetica, Arial, sans-serif">'
                f'<rect width="{W}" height="{h}" fill="{PAPER}"/>' + "".join(s.p) + "</svg>")

def header(s, title, sub):
    s.y = PAD
    s.para(PAD, title, W - 2 * PAD, 19, INK, True, 25)
    s.y += 2
    s.para(PAD, sub, W - 2 * PAD, 15, MUTED, False, 21)
    s.y += 12

# The test-flow diagram is drawn by make_flow.py.

# ---------------------------------------------------------------- 2. caught
s = Svg(); header(s, "Asking three times caught the mistakes the check missed",
                  "Wrong first answers from the four cheap models, 81 held-out tasks each: 20 in total")
BW = W - 2 * PAD
def stacked(label, caught, total, note):
    s.para(PAD, label, BW, 16, INK, True, 22); s.y += 4
    y = s.y; u = BW / total
    s.rect(PAD, y, BW, 34, MISS, rx=6)
    if caught: s.rect(PAD, y, caught * u, 34, GREEN, rx=6)
    if caught and caught < total: s.rect(PAD + caught * u - 6, y, 6, 34, GREEN, rx=0)
    cx = PAD + caught * u
    if caught >= 3: s.text(PAD + 10, y + 23, f"caught {caught}", 15, "#FFFFFF", True)
    s.text(PAD + BW - 10, y + 23, f"missed {total - caught}", 15, INK, False, "end")
    s.y += 34 + 4
    s.para(PAD, note, BW, 15, MUTED, False, 21); s.y += 14
stacked("Code check: caught 1 of 20", 1, 20, "The one it caught had run out of room before it gave any answer.")
stacked("Asking three times: caught 13 of 20", 13, 20, "It missed 7 where all three answers agreed on the same wrong answer. It also sent 19 right answers to Sol, which costs money.")
s.y += 2; s.p.append(f'<line x1="{PAD}" y1="{s.y}" x2="{W-PAD}" y2="{s.y}" stroke="{RULE}"/>'); s.y += 4
s.para(PAD, "Each model’s first answer only. Run of 29 Oct.", BW, 15, MUTED, False, 21)
open("e06-caught-2026-10-31.svg", "w").write(s.svg())

# ---------------------------------------------------------------- 3. cost
s = Svg(); header(s, "Sol’s accuracy for about a quarter of the price",
                  "gpt-oss-20b on 81 held-out tasks. Bars show cost per 1,000 tasks.")
rows = [("gpt-oss-20b alone", "91.8% right", 0.0685, MISS), ("+ code check", "91.8% right", 0.0685, MISS),
        ("+ asking three times", "97.5% right", 0.4033, GREEN), ("Sol alone", "97.5% right", 1.5082, ACC)]
maxw = BW - 58
for label, acc, cost, col in rows:
    y0 = s.y + 18
    s.text(PAD, y0, label, 16, INK, True); s.text(W - PAD, y0, acc, 15, MUTED, False, "end")
    s.y = y0 + 8
    w = max(4, maxw * cost / 1.5082)
    s.rect(PAD, s.y, w, 24, col, rx=5)
    s.text(PAD + w + 8, s.y + 17, f"${cost:.2f}", 15, INK, True)
    s.y += 24 + 14
s.p.append(f'<line x1="{PAD}" y1="{s.y}" x2="{W-PAD}" y2="{s.y}" stroke="{RULE}"/>'); s.y += 4
s.para(PAD, "With three answers, the other cheap models scored 95–99% at $0.41–$0.62. List prices; run of 29 Oct.", BW, 15, MUTED, False, 21)
open("e06-cost-2026-10-31.svg", "w").write(s.svg())
print("ok")
