"""400-unit publication canvas; 480px display; 960px PNG. Charts require approved held-out results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from e2core import E06, sha, write_json  # noqa: E402
from freeze import require_approval  # noqa: E402

INK, MUTED, RULE, PAPER = "#1A1D24", "#4A5160", "#D9D6CF", "#FCFBF9"
ACCENT, AMBER, GREEN = "#8F5A0E", "#E0A946", "#2D6B45"
HERE = Path(__file__).resolve().parent


def setup(font):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    font = font or E06 / "chart-assets/InterVariable.ttf"
    if not font.exists():
        raise ValueError("Inter font not found. Supply --font PATH; no silent substitution is permitted.")
    font_manager.fontManager.addfont(str(font))
    family = font_manager.FontProperties(fname=font).get_name()
    if "Inter" not in family:
        raise ValueError("The supplied font must be Inter")
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 10.8,
            "svg.fonttype": "none",
            "axes.edgecolor": RULE,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": MUTED,
            "ytick.color": INK,
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "savefig.facecolor": PAPER,
        }
    )
    return plt, font


def canvas(plt, height):
    fig = plt.figure(figsize=(4, height / 100), dpi=240)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set(xlim=(0, 400), ylim=(height, 0))
    ax.axis("off")
    return fig, ax


def text(ax, x, y, value, size=15, color=INK, weight="normal", ha="center"):
    return ax.text(x, y, value, fontsize=size * 0.72, color=color, weight=weight, ha=ha, va="center", linespacing=1.25)


def arrow(ax, x1, y1, x2, y2):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops={"arrowstyle": "->", "color": MUTED, "lw": 1.0})


def save(plt, fig, basename, caption, metadata):
    # No bbox_inches='tight': preserve the exact 400-unit canvas and 960px width.
    fig.savefig(HERE / f"{basename}.png", dpi=240)
    fig.savefig(HERE / f"{basename}.svg", metadata={"Date": None})
    svg = HERE / f"{basename}.svg"
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (HERE / f"{basename}.txt").write_text(caption + "\n", encoding="utf-8", newline="\n")
    write_json(HERE / f"{basename}.json", metadata)
    plt.close(fig)


def flow(plt, font):
    fig, ax = canvas(plt, 560)
    text(ax, 16, 28, "When an LLM call fails", 22, weight="bold", ha="left")
    text(ax, 16, 61, "Four designs, following the failure path.", 15, MUTED, ha="left")
    text(ax, 200, 112, "Failed call", 18, weight="bold")
    ax.plot([200, 200], [132, 153], color=MUTED, lw=1)
    ax.plot([50, 350], [153, 153], color=MUTED, lw=1)
    xs = (50, 150, 250, 350)
    for x, label in zip(xs, ("Default", "Retry", "Fallback", "Say so"), strict=True):
        arrow(ax, x, 153, x, 184)
        text(ax, x, 205, label, weight="bold")
    for x, label in zip(xs[1:], ("Retry\nup to 2x", "Retry\nonce", "Retry\nonce"), strict=True):
        arrow(ax, x, 224, x, 248)
        text(ax, x, 273, label)
    arrow(ax, 50, 224, 50, 414)
    arrow(ax, 150, 304, 150, 414)
    arrow(ax, 250, 304, 250, 328)
    text(ax, 250, 353, "Fallback\nonce", color=ACCENT)
    arrow(ax, 250, 384, 250, 414)
    arrow(ax, 350, 304, 350, 414)
    for x, label, color in zip(
        xs,
        ("Default\nvalue", "Default\nvalue", "Can't\ncheck", "Can't\ncheck"),
        (ACCENT, ACCENT, GREEN, GREEN),
        strict=True,
    ):
        text(ax, x, 447, label, 16, color, "bold")
        text(ax, x, 492, "Completed" if x < 200 else "Explicit", 15, MUTED)
    text(ax, 16, 535, "A usable response ends recovery early.", 15, MUTED, ha="left")
    save(
        plt,
        fig,
        "e02-recovery-flow",
        "Failure paths for four recovery designs. A usable response ends "
        "recovery early. Default and exhausted retries emit completed defaults; fallback and say-so emit "
        "explicit couldn't-check results on exhaustion.",
        {
            "canvas_units": [400, 560],
            "display_width_px": 480,
            "png_width_px": 960,
            "minimum_type_units": 15,
            "font_sha256": sha(font),
            "data": "policy diagram, no outcome claims",
        },
    )


def chart(plt, font, analysis):
    from matplotlib.ticker import MaxNLocator

    review = require_approval()
    verification = json.loads((analysis / "verification.json").read_text(encoding="utf-8"))
    for name, expected in verification["output_sha256"].items():
        if sha(analysis / name) != expected:
            raise ValueError("Analysis output changed: " + name)
    summary = json.loads((analysis / "summary.json").read_text(encoding="utf-8"))
    if (
        summary["mode"] != "approved_evaluation"
        or summary["cohort"] != "heldout"
        or verification["review_sha256"] != review
    ):
        raise ValueError("Charts require approved held-out evaluation; pilot charts are blocked")
    uncertainty = json.loads((analysis / "uncertainty.json").read_text(encoding="utf-8"))
    scenario, variant = "independent-20-timeout", "zero_numeric"
    rows = summary["scenarios"][scenario][variant]["all"]
    ci = uncertainty["scenarios"][scenario][variant]["all"]
    designs = ("default", "retry", "fallback", "say_so")
    labels = ("Default", "Retry", "Fallback", "Say so")
    values = [rows[d]["point"]["wrong_per_1000"] for d in designs]
    intervals = [ci[d]["wrong_per_1000"]["item_ci95"] for d in designs]
    maximum = max(10, max(pair[1] for pair in intervals)) * 1.30
    fig, title_ax = canvas(plt, 445)
    text(title_ax, 16, 28, "Wrong results shown", 22, weight="bold", ha="left")
    text(title_ax, 16, 62, "Independent 20% timeouts", 16, MUTED, ha="left")
    text(title_ax, 16, 88, "Per 1,000 tasks; 95% item intervals", 15, MUTED, ha="left")
    ax = fig.add_axes((0.25, 0.27, 0.69, 0.46))
    ax.barh(range(4), values, color=[AMBER, INK, INK, GREEN], height=0.48)
    for index, (value, bounds) in enumerate(zip(values, intervals, strict=True)):
        ax.plot(bounds, [index, index], color=ACCENT, lw=1.4)
        for bound in bounds:
            ax.plot([bound, bound], [index - 0.12, index + 0.12], color=ACCENT, lw=1)
        ax.text(max(value, bounds[1]) + maximum * 0.025, index, f"{value:.1f}", va="center", fontsize=10.8)
    ax.set_yticks(range(4), labels)
    ax.set_xlim(0, maximum)
    ax.invert_yaxis()
    ax.tick_params(axis="both", labelsize=10.8, length=0, pad=5)
    ax.xaxis.set_major_locator(MaxNLocator(3))
    ax.grid(axis="x", color=RULE, alpha=0.6)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    text(title_ax, 16, 365, "Synthetic tasks; repeated saved answers.", 15, MUTED, ha="left")
    text(title_ax, 16, 391, "Unverified tool defaults shown separately", 15, MUTED, ha="left")
    text(title_ax, 16, 417, "in the accompanying results table.", 15, MUTED, ha="left")
    caption = (
        "Wrong completed results per 1,000 tasks under assumed independent 20% timeouts; "
        "zero-numeric defaults; reused E06 held-out cohort. "
        + "; ".join(f"{label}: {value:.2f}" for label, value in zip(labels, values, strict=True))
        + ". Intervals resample whole items and do not capture failure-model or template uncertainty. "
        "Unverified tool no-ops are excluded from wrong and reported separately."
    )
    save(
        plt,
        fig,
        "e02-wrong-results",
        caption,
        {
            "canvas_units": [400, 445],
            "display_width_px": 480,
            "png_width_px": 960,
            "minimum_type_units": 15,
            "font_sha256": sha(font),
            "summary_sha256": sha(analysis / "summary.json"),
            "uncertainty_sha256": sha(analysis / "uncertainty.json"),
            "source_path": f"scenarios.{scenario}.{variant}.all.<design>.point.wrong_per_1000",
            "values": dict(zip(designs, values, strict=True)),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--flow-only", action="store_true")
    mode.add_argument("--analysis", type=Path)
    args = parser.parse_args()
    plt, font = setup(args.font)
    flow(plt, font)
    if args.analysis:
        chart(plt, font, args.analysis.resolve())
    print("Wrote publication assets to " + str(HERE))


if __name__ == "__main__":
    main()
