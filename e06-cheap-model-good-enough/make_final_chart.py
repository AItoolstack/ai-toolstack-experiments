"""Export the held-out cost/accuracy chart as a 2x PNG and SVG, using saved results only."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent
INK, MUTED, RULE, PAPER, ACCENT, AMBER = "#1A1D24", "#4A5160", "#D9D6CF", "#FCFBF9", "#8F5A0E", "#E0A946"


def main():
    source = ROOT / "analysis_frozen_20261029_heldout" / "summary-v2.json"
    summary = json.loads(source.read_text(encoding="utf-8"))
    font_path = ROOT / "chart-assets" / "InterVariable.ttf"
    font_manager.fontManager.addfont(str(font_path))
    font = font_manager.FontProperties(fname=str(font_path))
    plt.rcParams.update(
        {
            "font.family": font.get_name(),
            "font.size": 11.5,
            "text.color": INK,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "svg.fonttype": "path",
        }
    )
    fig = plt.figure(figsize=(6.6, 6.8), dpi=100)
    fig.text(0.09, 0.946, "Checks rarely escalated.", fontsize=19, fontweight="bold")
    fig.text(0.09, 0.903, "Agreement added cost and improved observed scores.", fontsize=11.5, color=MUTED)
    ax = fig.add_axes([0.12, 0.39, 0.82, 0.45])
    colors = {"oss-20b": INK, "luna": ACCENT, "glm-flash": AMBER, "oss-120b": MUTED}
    names = {"oss-20b": "OSS-20B", "luna": "Luna", "glm-flash": "GLM Flash", "oss-120b": "OSS-120B"}
    baseline = summary["models"]["sol"]["all"]
    ax.axhline(100 * baseline["accuracy"], color=RULE, linewidth=1.3, linestyle="--", zorder=0)
    for model, color in colors.items():
        alone = summary["models"][model]["all"]
        check = summary["cascades"][model]["all"]["check"]
        agreement = summary["cascades"][model]["all"]["agreement"]
        # Larger hollow squares show check policies even where they coincide with alone.
        ax.scatter(
            check["usd_per_1k_items"],
            100 * check["accuracy"],
            s=145,
            marker="s",
            facecolors=PAPER,
            edgecolors=color,
            linewidths=1.4,
            zorder=2,
        )
        ax.scatter(
            alone["usd_per_1k"],
            100 * alone["accuracy"],
            s=47,
            marker="o",
            facecolors=color,
            edgecolors=INK,
            linewidths=0.55,
            zorder=3,
        )
        ax.scatter(
            agreement["usd_per_1k_items"],
            100 * agreement["accuracy"],
            s=100,
            marker="^",
            facecolors=color,
            edgecolors=INK,
            linewidths=0.7,
            zorder=3,
        )
    control = summary["models"]["glm-flash-t0"]["all"]
    ax.scatter(
        control["usd_per_1k"],
        100 * control["accuracy"],
        s=75,
        marker="D",
        facecolors=PAPER,
        edgecolors=ACCENT,
        linewidths=1.6,
        zorder=3,
    )
    ax.scatter(baseline["usd_per_1k"], 100 * baseline["accuracy"], s=180, marker="*", color=INK, zorder=4)
    ax.annotate(
        "Sol alone",
        (baseline["usd_per_1k"], 100 * baseline["accuracy"]),
        xytext=(-8, 15),
        textcoords="offset points",
        ha="right",
        fontsize=11.5,
    )
    ax.set_xscale("log")
    ax.set(
        xlim=(0.05, 2), ylim=(90, 100.3), xlabel="USD per 1,000 items (log scale)", ylabel="Whole-answer accuracy (%)"
    )
    ax.set_xticks([0.05, 0.1, 0.2, 0.5, 1, 2], labels=["0.05", "0.10", "0.20", "0.50", "1", "2"])
    ax.set_yticks([90, 92, 94, 96, 98, 100])
    ax.minorticks_off()
    ax.grid(axis="y", color=RULE, linewidth=0.7)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        ax.spines[side].set_color(RULE)
    policy_handles = [
        Line2D([], [], marker="o", color="none", markerfacecolor=INK, markeredgecolor=INK, label="Alone", markersize=6),
        Line2D(
            [],
            [],
            marker="s",
            color="none",
            markerfacecolor=PAPER,
            markeredgecolor=INK,
            label="Code check",
            markersize=9,
        ),
        Line2D(
            [],
            [],
            marker="^",
            color="none",
            markerfacecolor=INK,
            markeredgecolor=INK,
            label="3-run agreement",
            markersize=8,
        ),
    ]
    fig.legend(
        handles=policy_handles,
        loc="upper left",
        bbox_to_anchor=(0.085, 0.30),
        ncol=3,
        frameon=False,
        handletextpad=0.45,
        columnspacing=1.0,
        fontsize=11.5,
    )
    model_handles = [Line2D([], [], color=c, linewidth=4, label=names[m]) for m, c in colors.items()]
    model_handles += [
        Line2D(
            [],
            [],
            color="none",
            marker="D",
            markeredgecolor=ACCENT,
            markerfacecolor=PAPER,
            label="GLM at temperature 0",
            markersize=6,
        ),
        Line2D(
            [],
            [],
            color="none",
            marker="*",
            markerfacecolor=INK,
            markeredgecolor=INK,
            label="Sol reference",
            markersize=10,
        ),
    ]
    fig.legend(
        handles=model_handles,
        loc="upper left",
        bbox_to_anchor=(0.085, 0.235),
        ncol=2,
        frameon=False,
        handlelength=1.0,
        handletextpad=0.7,
        columnspacing=2.2,
        fontsize=11.5,
    )
    fig.text(0.09, 0.071, "81 held-out synthetic items · 29 October 2026", fontsize=11.5, color=MUTED)
    fig.text(
        0.09, 0.032, "Observed scores do not establish equal reliability.  |  ai·toolstack", fontsize=11.5, color=MUTED
    )
    out = source.parent / "figures"
    out.mkdir(exist_ok=True)
    stem = "e06-cost-accuracy-2026-10-29"
    fig.savefig(out / (stem + ".png"), dpi=200, facecolor=PAPER)
    fig.savefig(out / (stem + ".svg"), facecolor=PAPER)
    plt.close(fig)
    alt = (
        "Cost and accuracy on 81 held-out synthetic items. Alone: OSS-20B 91.77% at $0.0685 per 1,000 items; "
        "Luna 96.71% at $0.0878; GLM Flash 91.77% at $0.1305; OSS-120B 95.88% at $0.1657; "
        "Sol 97.53% at $1.5082; GLM temperature-zero control 93.83% at $0.1263. "
        "Three-run agreement with Sol fallback: OSS-20B 97.53% at $0.4033; Luna 98.77% at $0.4065; "
        "GLM 95.06% at $0.6067; OSS-120B 97.53% at $0.6193. Code-check policies coincide with alone "
        "except GLM, which reaches 92.59% at $0.1445. Agreement charges all three cheap calls. "
        "Close observed scores do not establish equivalent production reliability."
    )
    caption = (
        "Code checks caught 2 of 58 wrong held-out cheap-model answers. Three-run agreement improved "
        "observed accuracy at $0.40–$0.62 per 1,000 items, versus $1.51 for Sol alone. "
        "These small synthetic cohorts do not establish equal reliability."
    )
    (out / (stem + ".txt")).write_text("Alt text: " + alt + "\n\nCaption: " + caption + "\n", encoding="utf-8")
    print(f"Wrote {out / (stem + '.png')} (1320 × 1360), SVG and alt/caption text.")


if __name__ == "__main__":
    main()
