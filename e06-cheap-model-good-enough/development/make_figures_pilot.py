"""Reproduce E06 charts from an analysis summary, without API calls.

python make_figures.py --summary analysis_samples_v2/summary-v2.json
Requires matplotlib (the runner, scorer and tests use only the standard library).
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary", default="analysis_samples_v2/summary-v2.json")
    args = ap.parse_args()
    source = Path(__file__).resolve().parent / args.summary
    summary = json.loads(source.read_text(encoding="utf-8"))
    out = source.parent / "figures"
    out.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "figure.facecolor": "#FCFBF9",
            "axes.facecolor": "#FCFBF9",
            "text.color": "#1A1D24",
            "axes.labelcolor": "#4A5160",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    models = list(summary["models"])
    pilot = summary["expected_repeats"] == 1
    qualifier = "Pilot · one repeat · synthetic samples" if pilot else "Synthetic evaluation items · repeated calls"

    def save(fig, name):
        fig.text(0.02, 0.015, qualifier + " | ai·toolstack", fontsize=9, color="#4A5160")
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        for ext in ("png", "svg"):
            fig.savefig(out / f"{name}.{ext}", dpi=170)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ("#1F2940", "#2F5FA8", "#E0A946")
    for offset, task in enumerate(("invoice", "tool", "rules")):
        for x, model in enumerate(models):
            data = summary["models"][model].get(task)
            if data is None:
                continue
            pos = x + (offset - 1) * 0.24
            ax.bar(pos, data["accuracy"] * 100, width=0.22, color=colors[offset], label=task if x == 0 else None)
            ax.text(
                pos,
                data["accuracy"] * 100 + 2,
                f"{round(data['accuracy'] * data['n'])}/{data['n']}",
                ha="center",
                fontsize=10,
            )
    ax.set(
        xticks=range(len(models)),
        xticklabels=models,
        ylim=(0, 119),
        ylabel="Whole answers correct (%)",
        title="How often was each model right?",
    )
    ax.legend(frameon=False, ncol=3, loc="upper right")
    save(fig, "f1-task-accuracy")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, version in zip(axes, ("baseline", "v2"), strict=True):
        for y, model in enumerate(models):
            data = summary["checks_by_version"][model][version]["all"]
            ax.barh(y, data["wrong_caught"], color="#2D6B45", label="Caught" if y == 0 else None)
            ax.barh(
                y,
                data["wrong_accepted"],
                left=data["wrong_caught"],
                color="#E0A946",
                label="Passed checks" if y == 0 else None,
            )
            ax.text(
                data["wrong_caught"] + data["wrong_accepted"] + 0.2,
                y,
                (
                    f"{data['wrong_accepted']} escaped"
                    if data["wrong_caught"] + data["wrong_accepted"]
                    else "No incorrect answers"
                ),
                va="center",
                fontsize=10,
            )
        ax.set(
            yticks=range(len(models)),
            yticklabels=models,
            xlabel="Incorrect answers (count)",
            title="Original checks" if version == "baseline" else "Revised checks (after seeing pilot)",
        )
        ax.set_xlim(
            0,
            max(
                3,
                max(
                    summary["checks_by_version"][m][version]["all"]["wrong_caught"]
                    + summary["checks_by_version"][m][version]["all"]["wrong_accepted"]
                    for m in models
                ),
            )
            + 4,
        )
        ax.legend(frameon=False, loc="upper right")
    fig.suptitle("Which mistakes did code catch?")
    save(fig, "f2-errors-caught-and-missed")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    points = 0
    for model, tasks in summary["cascades"].items():
        for mode, data in tasks.get("all", {}).items():
            if data["status"] != "complete":
                continue
            x, y = data["usd_per_1k_items"], data["accuracy"] * 100
            ax.scatter(x, y, s=70)
            ax.annotate(
                f"{model} + {mode}",
                (x, y),
                xytext=(6, -15 if mode == "agreement" else 6),
                textcoords="offset points",
                fontsize=10,
            )
            points += 1
    for model in models:
        if not summary["coverage"][model]["complete"]:
            continue
        data = summary["models"][model]["all"]
        ax.scatter(data["usd_per_1k"], data["accuracy"] * 100, marker="x", s=80, color="#1F2940")
        ax.annotate(
            model + " alone",
            (data["usd_per_1k"], data["accuracy"] * 100),
            xytext=(6, -18),
            textcoords="offset points",
            fontsize=10,
        )
        points += 1
    if not points:
        ax.text(0.5, 0.5, "No complete comparison cohort", transform=ax.transAxes, ha="center")
    ax.set(
        xlabel="Listed token cost per 1,000 items (USD)",
        ylabel="Whole answers correct (%)",
        ylim=(0, 110),
        title="Cost and accuracy on the same items",
    )
    ax.margins(x=0.25)
    ax.set_xlim(left=0)
    save(fig, "f3-cost-and-accuracy")
    print(f"Wrote PNG and SVG charts to {out}")


if __name__ == "__main__":
    main()
