"""E06 test flow as a fork: same three cheap answers, two rules, each keeps answer 1 or uses Sol."""
INK, MUTED, RULE, PAPER, ACC = "#1A1D24", "#4A5160", "#D9D6CF", "#FCFBF9", "#8F5A0E"
GREEN, GREEN_BG, GREY_BG, AMBER_BG = "#2D6B45", "#E7F2EA", "#F1EFEA", "#FAEEDD"
W, H = 400, 560
p = []
def rect(x, y, w, h, fill=GREY_BG, stroke=RULE, sw=1.5, rx=8):
    p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def text(x, y, t, size=15, fill=INK, bold=False, anchor="middle"):
    p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{fill}" text-anchor="{anchor}">{t}</text>')
def arrow(x1, y1, x2, y2, color=MUTED, label=None, lx=0, ly=0, lcolor=MUTED):
    p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6" marker-end="url(#ah)"/>')
    if label: text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, 15, lcolor, True)
def diamond(cx, cy, w, h, fill, stroke):
    p.append(f'<path d="M{cx},{cy-h/2} L{cx+w/2},{cy} L{cx},{cy+h/2} L{cx-w/2},{cy} Z" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')

# title
text(14, 30, "How each answer was tested", 19, INK, True, "start")
# 1. task
rect(100, 50, 200, 40); text(200, 76, "Task + written answer", 15, INK, True)
arrow(200, 90, 200, 112)
# 2. cheap model, three answers
rect(60, 114, 280, 74, "#FFFFFF", RULE)
text(200, 138, "Cheap model, asked 3 times", 15, INK, True)
for i, x in enumerate((112, 200, 288)):
    rect(x - 36, 150, 72, 28, GREY_BG, RULE, 1.2, 6); text(x, 169, f"answer {i+1}", 15, MUTED)
# fork
arrow(112, 188, 102, 226); arrow(288, 188, 298, 226)
# 3. decisions: rule name + question
rect(14, 228, 176, 62, GREY_BG, MUTED); text(102, 253, "Rule 1: code check", 15, INK, True); text(102, 275, "Answer 1 well formed?", 15, MUTED)
rect(210, 228, 176, 62, GREEN_BG, GREEN, 2); text(298, 253, "Rule 2: agreement", 15, GREEN, True); text(298, 275, "All 3 the same?", 15, MUTED)
# outcomes row
rect(14, 370, 110, 52, "#FFFFFF", RULE); text(69, 393, "Keep", 15, INK, True); text(69, 412, "answer 1", 15, MUTED)
rect(276, 370, 110, 52, "#FFFFFF", RULE); text(331, 393, "Keep", 15, INK, True); text(331, 412, "answer 1", 15, MUTED)
rect(140, 370, 120, 52, AMBER_BG, ACC); text(200, 393, "Use Sol", 15, ACC, True); text(200, 412, "(expensive)", 15, MUTED)
# yes / no arrows
arrow(60, 290, 60, 366, MUTED, "yes", -20, 0)
arrow(150, 290, 176, 366, MUTED, "no", 18, -2)
arrow(340, 290, 340, 366, MUTED, "yes", 20, 0)
arrow(250, 290, 224, 366, MUTED, "no", -18, -2)
# 4. marked
for x in (69, 200, 331):
    arrow(x, 422, 200 + (x - 200) * 0.35, 470)
rect(80, 472, 240, 44, PAPER, INK, 1.6); text(200, 499, "Marked by code. No AI judge.", 15, INK, True)
text(14, 546, "Both rules ran on the same saved answers.", 15, MUTED, False, "start")
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="480" height="{round(H*1.2)}" role="img" '
       f'aria-label="Two rules decide whether to keep a cheap model answer or use Sol" '
       f'font-family="Inter, \'Segoe UI\', system-ui, -apple-system, Helvetica, Arial, sans-serif">'
       f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
       f'<path d="M0,0 L10,5 L0,10 Z" fill="{MUTED}"/></marker></defs>'
       f'<rect width="{W}" height="{H}" fill="{PAPER}"/>' + "".join(p) + "</svg>")
open("e06-test-flow-2026-10-31.svg", "w").write(svg)
