"""Builds the E01 write-up figures from the raw results, in the ai-toolstack.com brand.

SVG files use the site's CSS variables (with fallbacks), so they also render standalone.
Writes figures/*.svg and figures/*.html (the HTML grids are used in the blog post)."""

import collections
import os
from html import escape

from common import DISPUTED, HERE, JUDGES, load_items, load_runs

OUT = os.path.join(HERE, "figures")
items = load_items("items_v2.jsonl")
runs = load_runs("items_v2.jsonl")
FILES = {name: stem for stem, name in JUDGES.items()}
JUDGE_NAMES = list(FILES)
COST = {"gpt-oss-120b": "$0.12", "gpt-oss-120b, temp 0": "$0.13", "GPT-6 Luna": "$0.09", "GPT-6.1 Sol": "$1.19"}
rows = {name: runs[stem] for name, stem in FILES.items()}
counts = {j: collections.defaultdict(collections.Counter) for j in JUDGE_NAMES}
for j in JUDGE_NAMES:
    for r in rows[j]:
        counts[j][r["item"]][r["verdict"]] += 1

C = dict(
    ink="var(--ink,#1A1D24)",
    muted="var(--muted,#4A5160)",
    dim="var(--dim,#8A909C)",
    rule="var(--rule,#ECEAE5)",
    paper="var(--paper,#F6F5F1)",
    card="var(--card-bg,#FCFBF9)",
    navy="var(--navy,#1F2940)",
    amber="var(--amber,#E0A946)",
    accent="var(--accent,#8F5A0E)",
    blue="var(--doc-ink,#2F5FA8)",
    bluebg="var(--doc,#E8EFFA)",
    green="var(--build-ink,#2D6B45)",
    greenbg="var(--build,#E7F2EA)",
    warm="var(--prod-ink,#8F5A0E)",
    warmbg="var(--prod,#FAEEDD)",
)
FONT = "var(--font-sans,Geist,ui-sans-serif,system-ui,sans-serif)"


def svg(w, h, body, title):
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{escape(title)}" '
        f'xmlns="http://www.w3.org/2000/svg" style="font-family:{FONT};max-width:{w}px;height:auto;display:block;margin:0 auto">'
        f"<title>{escape(title)}</title>{body}</svg>"
    )


def t(x, y, s, size=18, fill=C["ink"], weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(s))}</text>'


def save(name, s):
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(s)


# ---------- F1: what we tested ----------
def f1():
    W, H = 680, 470
    b = [f'<rect width="{W}" height="{H}" fill="{C["card"]}" rx="12"/>']

    def box(x, y, w, h, head, lines, fill, ink):
        out = [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}"/>',
            t(x + 16, y + 32, head, 19, ink, 700),
        ]
        for k, ln in enumerate(lines):
            out.append(t(x + 16, y + 62 + k * 24, ln, 16, C["muted"]))
        return "".join(out)

    b.append(t(24, 40, "One check, start to finish", 21, C["ink"], 700))
    b.append(
        box(
            24,
            62,
            196,
            170,
            "1. An item",
            ["a document", "+ an answer to mark", "", "e.g. a support reply", "and the returns policy"],
            C["bluebg"],
            C["blue"],
        )
    )
    b.append(
        box(
            242,
            62,
            196,
            170,
            "2. An AI judge",
            ["reads the item and a", "marking guide", "", "4 judges: gpt-oss (x2),", "Luna, Sol"],
            C["paper"],
            C["navy"],
        )
    )
    b.append(
        box(
            460,
            62,
            196,
            170,
            "3. A mark",
            ["PASS or FAIL,", "or a score from 1 to 5,", "", "plus a one-line", "reason"],
            C["greenbg"],
            C["green"],
        )
    )
    for x in (222, 440):
        b.append(
            f'<path d="M{x} 147 l16 0" stroke="{C["dim"]}" stroke-width="2"/><path d="M{x + 16} 141 l6 6 l-6 6" fill="none" stroke="{C["dim"]}" stroke-width="2"/>'
        )
    b.append(
        t(
            24,
            270,
            "Each judge marked every item 13 times: 30 items × 13 runs × 4 judges = 1,560 marks.",
            15.5,
            C["muted"],
        )
    )
    b.append(t(24, 318, "The 30 items", 19, C["ink"], 700))
    groups = [("Document checks", "faithfulness"), ("Summary scores", "summary_score"), ("Policy checks", "policy")]
    x0, bw, y0 = 24, 204, 336
    for g, (label, task) in enumerate(groups):
        ids = [i for i, it in items.items() if it["task"] == task]
        clear = sum(items[i]["kind"] == "clear" for i in ids)
        x = x0 + g * (bw + 10)
        cw = bw * clear / len(ids)
        b.append(f'<rect x="{x}" y="{y0}" width="{cw - 2}" height="44" rx="6" fill="{C["navy"]}"/>')
        b.append(f'<rect x="{x + cw}" y="{y0}" width="{bw - cw}" height="44" rx="6" fill="{C["amber"]}"/>')
        b.append(t(x + 10, y0 + 28, f"{clear} clear", 15, "#FFFFFF", 600))
        b.append(t(x + cw + 8, y0 + 28, f"{len(ids) - clear}", 15, C["ink"], 600))
        b.append(t(x, y0 + 70, label, 16, C["ink"], 600))
        b.append(t(x, y0 + 92, "PASS/FAIL" if task != "summary_score" else "score 1 to 5", 14, C["muted"]))
    b.append(
        f'<rect x="24" y="{H - 28}" width="14" height="14" rx="3" fill="{C["navy"]}"/>'
        + t(44, H - 16, "clear right answer", 14, C["muted"])
    )
    b.append(
        f'<rect x="196" y="{H - 28}" width="14" height="14" rx="3" fill="{C["amber"]}"/>'
        + t(216, H - 16, "borderline on purpose", 14, C["muted"])
    )
    save(
        "f1-what-we-tested.svg",
        svg(W, H, "".join(b), "Diagram: an item goes to an AI judge, which gives a mark. 30 items, 13 runs, 4 judges."),
    )


# ---------- bar helper ----------
def hbars(name, title, sub, values, vmax, fmt, note=None, rng=None, key=None, xlabel=None, vmin=0, sub2=None):
    W = 680
    top = 96
    rowh = 74
    H = top + rowh * len(values) + (70 if note or xlabel else 30)
    lx, bx, bw = 24, 236, 270

    def X(v):
        return bx + bw * (v - vmin) / (vmax - vmin)

    b = [
        f'<rect width="{W}" height="{H}" fill="{C["card"]}" rx="12"/>',
        t(24, 40, title, 21, C["ink"], 700),
        t(24, 66, sub, 15, C["muted"]),
    ]
    if key is not None:
        kx = X(key)
        b.append(
            f'<line x1="{kx}" y1="{top - 6}" x2="{kx}" y2="{top + rowh * len(values) - 18}" stroke="{C["accent"]}" stroke-width="2" stroke-dasharray="5 4"/>'
        )
        b.append(t(kx, top - 12, f"my answer key: {key}", 14, C["accent"], 700, "middle"))
    for k, (label, v) in enumerate(values):
        y = top + k * rowh
        b.append(t(lx, y + 22, label, 17, C["ink"], 600))
        b.append(t(lx, y + 44, f"{COST[label]} per 1,000 marks", 13.5, C["dim"]))
        if rng:
            lo, hi = rng[label]
            b.append(
                f'<line x1="{X(lo)}" y1="{y + 28}" x2="{X(hi)}" y2="{y + 28}" stroke="{C["blue"]}" stroke-opacity=".3" stroke-width="14" stroke-linecap="round"/>'
            )
            b.append(f'<circle cx="{X(v)}" cy="{y + 28}" r="9" fill="{C["blue"]}" stroke="#fff" stroke-width="2"/>')
        else:
            b.append(f'<rect x="{bx}" y="{y + 12}" width="{bw}" height="30" rx="5" fill="{C["paper"]}"/>')
            b.append(f'<rect x="{bx}" y="{y + 12}" width="{max(4, X(v) - bx)}" height="30" rx="5" fill="{C["navy"]}"/>')
        b.append(t(bx + bw + 16, y + 26, fmt(label, v), 17, C["ink"], 700))
        if sub2:
            b.append(t(bx + bw + 16, y + 46, sub2(label), 13.5, C["muted"]))
    if xlabel:
        b.append(t(bx, H - 36, xlabel, 14, C["muted"]))
    if note:
        b.append(t(24, H - 14, note, 14.5, C["muted"]))
    save(name, svg(W, H, "".join(b), title + ("" if title.endswith("?") else ".") + " " + sub))


def f2():
    ids = [
        i for i, it in items.items() if it["kind"] == "clear" and it["task"] != "summary_score" and i not in DISPUTED
    ]
    vals, rng = [], {}
    for j in JUDGE_NAMES:
        per = collections.Counter()
        for r in rows[j]:
            if r["item"] in ids:
                per[r["repeat"]] += r["verdict"] == items[r["item"]]["label"]
        v = list(per.values())
        vals.append((j, sum(v) / 13))
        rng[j] = (min(v), max(v))
    hbars(
        "f2-accuracy.svg",
        f"Right answers on {len(ids)} clear pass-or-fail items",
        "Average of 13 runs per judge.",
        vals,
        len(ids),
        lambda j, v: f"{v:.1f} of {len(ids)}",
        sub2=lambda j: "every run" if rng[j][0] == rng[j][1] else f"runs: {rng[j][0]} to {rng[j][1]}",
    )
    return {j: v for j, v in vals}, rng


def f4():
    W, H = 680, 380
    tasks = [("Document checks", "faithfulness"), ("Summary scores", "summary_score"), ("Policy checks", "policy")]
    b = [
        f'<rect width="{W}" height="{H}" fill="{C["card"]}" rx="12"/>',
        t(24, 40, "Same mark all 13 times?", 21, C["ink"], 700),
        t(24, 66, "Items where the judge never changed its mark, out of 10 per type.", 15, C["muted"]),
    ]
    pw = 196
    for g, (label, task) in enumerate(tasks):
        x0 = 24 + g * (pw + 18)
        b.append(t(x0, 110, label, 17, C["ink"], 700))
        ids = [i for i, it in items.items() if it["task"] == task]
        for k, j in enumerate(JUDGE_NAMES):
            y = 128 + k * 58
            n = sum(len(counts[j][i]) == 1 for i in ids)
            b.append(t(x0, y + 14, j, 14, C["muted"]))
            b.append(f'<rect x="{x0}" y="{y + 22}" width="{pw - 46}" height="20" rx="4" fill="{C["paper"]}"/>')
            b.append(
                f'<rect x="{x0}" y="{y + 22}" width="{(pw - 46) * n / 10}" height="20" rx="4" fill="{C["navy"] if task != "summary_score" else C["amber"]}"/>'
            )
            b.append(t(x0 + pw - 40, y + 38, f"{n}", 17, C["ink"], 700))
    b.append(
        t(
            24,
            H - 14,
            "Scores out of 5 changed most: there are five options, and 4 vs 5 is a judgement call.",
            14.5,
            C["muted"],
        )
    )
    save("f4-same-mark.svg", svg(W, H, "".join(b), "Same mark all 13 times, by judge and type of check"))


def f6():
    binary = [i for i, it in items.items() if it["task"] != "summary_score"]
    key = sum(items[i]["label"] == "PASS" for i in binary)
    vals, rng = [], {}
    order = ["GPT-6 Luna", "GPT-6.1 Sol", "gpt-oss-120b", "gpt-oss-120b, temp 0"]
    for j in order:
        per = collections.Counter()
        for r in rows[j]:
            if r["item"] in binary:
                per[r["repeat"]] += r["verdict"] == "PASS"
        v = list(per.values())
        vals.append((j, sum(v) / 13))
        rng[j] = (min(v), max(v))
    hbars(
        "f6-answers-passed.svg",
        "Same 20 answers. How many did each judge pass?",
        "Dot = average of 13 runs; bar = fewest to most. Higher means more lenient.",
        vals,
        16,
        lambda j, v: f"{v:.1f} of 20",
        rng=rng,
        key=key,
        vmin=6,
        sub2=lambda j: f"runs: {rng[j][0]} to {rng[j][1]}",
        xlabel="answers marked PASS (axis shows 6 to 16)",
    )
    return {j: v for j, v in vals}, rng, key


# ---------- HTML grids (reflow on phones) ----------
CSS = """<style>
.e1-wrap{overflow-x:auto;margin:1.5em 0}
.e1-grid{border-collapse:separate;border-spacing:3px;font-family:var(--font-sans);font-size:15px;min-width:560px;width:100%}
.e1-grid th{font-size:13px;font-weight:600;color:var(--muted,#4A5160);text-align:center;padding:4px 6px;vertical-align:bottom}
.e1-grid th:first-child,.e1-grid td:first-child{text-align:left}
.e1-grid td{padding:7px 8px;border-radius:6px;text-align:center;background:var(--paper,#F6F5F1)}
.e1-grid td.lab{background:transparent;color:var(--ink,#1A1D24);font-size:14.5px;line-height:1.3}
.e1-grid td.key{background:transparent;font-weight:700}
.e1-grid td.pass{background:var(--build,#E7F2EA);color:var(--build-ink,#2D6B45)}
.e1-grid td.fail{background:var(--prod,#FAEEDD);color:var(--prod-ink,#8F5A0E)}
.e1-grid td.same{background:var(--build,#E7F2EA);color:var(--build-ink,#2D6B45)}
.e1-grid td.diff{background:var(--prod,#FAEEDD);color:var(--prod-ink,#8F5A0E)}
.e1-grid td b{font-size:16px}
.e1-grid td small{display:block;font-size:11.5px;opacity:.85}
.e1-cap{font-size:13.5px;color:var(--muted,#4A5160);margin-top:.4em}
.e1-card{background:var(--card-bg,#FCFBF9);border:1px solid var(--rule,#ECEAE5);border-radius:12px;padding:18px 20px;margin:1.6em 0;font-size:16px}
.e1-card h4{margin:0 0 .6em;font-size:17px}
.e1-card .e1-k{font-family:var(--font-mono);font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim,#8A909C);margin:.9em 0 .25em}
.e1-card .e1-q{background:var(--paper,#F6F5F1);border-radius:8px;padding:10px 12px;font-size:15px;line-height:1.5}
.e1-card table{width:100%;border-collapse:collapse;font-size:15px;margin-top:.3em}
.e1-card td{padding:5px 4px;border-bottom:1px solid var(--rule,#ECEAE5)}
.e1-card td:last-child{text-align:right}
.e1-card .e1-ok{color:var(--build-ink,#2D6B45);font-weight:600}
.e1-card .e1-no{color:var(--prod-ink,#8F5A0E);font-weight:600}
.e1-card .e1-why{margin:.8em 0 0;font-size:15px;color:var(--ink-2,#22252C)}
</style>"""

SHORT = {
    "s01": "Incident: complete",
    "s02": "Incident: leaves out the actions",
    "s03": "Incident: rounded numbers",
    "s04": "Incident: invents refunds",
    "s05": "Incident: wrong cause",
    "s06": "Meeting: invents a decision",
    "s07": "Meeting: leaves out a risk and an action",
    "s08": "Meeting: complete",
    "s09": "Meeting: says 41% is below a 35% target",
    "s10": "Meeting: nearly empty",
    "f03": "“Failed requests aren’t billed”",
    "f04": "Adds “use backoff” advice",
    "f09": "“Your 75-day claim will be rejected”",
    "p05": "£5 voucher when we made no mistake",
    "p06": "Refund “in 5 days, often sooner”",
    "p08": "Asks for last 4 card digits",
    "p10": "Curt reply that follows the rules",
}


def cell(j, i):
    c = counts[j][i]
    top, n = c.most_common(1)[0]
    return top, n


def f3():
    ids = [f"s{n:02d}" for n in range(1, 11)]
    h = [
        '<div class="e1-wrap"><table class="e1-grid"><thead><tr><th>Summary</th><th>My score</th>'
        + "".join(f"<th>{escape(j)}</th>" for j in JUDGE_NAMES)
        + "</tr></thead><tbody>"
    ]
    for i in ids:
        tds = []
        for j in JUDGE_NAMES:
            top, n = cell(j, i)
            cls = "same" if top == items[i]["label"] else "diff"
            note = "all 13 runs" if n == 13 else f"{n} of 13 runs"
            tds.append(f'<td class="{cls}"><b>{top}</b><small>{note}</small></td>')
        h.append(
            f'<tr><td class="lab">{escape(SHORT[i])}</td><td class="key">{items[i]["label"]}</td>{"".join(tds)}</tr>'
        )
    h.append(
        '</tbody></table></div><p class="e1-cap">Each cell shows the score the judge gave most often, and in how many of its 13 runs. '
        "Green: same as my score. Amber: different from my score (which isn’t always the judge’s fault).</p>"
    )
    save("f3-summary-grid.html", "".join(h))


def f5():
    ids = [i for i, it in items.items() if it["kind"] == "contested"]
    h = [
        '<div class="e1-wrap"><table class="e1-grid"><thead><tr><th>Borderline item</th><th>My mark</th>'
        + "".join(f"<th>{escape(j)}</th>" for j in JUDGE_NAMES)
        + "<th>All four agree?</th></tr></thead><tbody>"
    ]
    agree = 0
    for i in ids:
        tds, tops = [], []
        for j in JUDGE_NAMES:
            top, n = cell(j, i)
            tops.append(top)
            cls = "pass" if top == "PASS" else "fail" if top == "FAIL" else ""
            note = "all 13 runs" if n == 13 else f"{n} of 13 runs"
            tds.append(f'<td class="{cls}"><b>{top}</b><small>{note}</small></td>')
        same = len(set(tops)) == 1
        agree += same
        h.append(
            f'<tr><td class="lab">{escape(SHORT[i])}</td><td class="key">{items[i]["label"]}</td>{"".join(tds)}'
            f'<td class="key">{"Yes" if same else "No"}</td></tr>'
        )
    h.append(
        f'</tbody></table></div><p class="e1-cap">Each cell shows the mark the judge gave most often, and in how many of its 13 runs. '
        f"All four judges agreed on {agree} of these {len(ids)} items.</p>"
    )
    save("f5-borderline-grid.html", "".join(h))
    clear = [i for i, it in items.items() if it["kind"] == "clear"]
    clear_agree = sum(len({cell(j, i)[0] for j in JUDGE_NAMES}) == 1 for i in clear)
    return agree, len(ids), clear_agree, len(clear)


if __name__ == "__main__":
    f1()
    acc = f2()
    f3()
    f4()
    passed = f6()
    ag = f5()
    save("style.html", CSS)
    print("accuracy", acc)
    print("passed", passed)
    print("agreement", ag)
