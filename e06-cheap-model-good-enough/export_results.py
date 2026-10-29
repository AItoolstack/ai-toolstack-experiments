"""Export all wrong answers and per-kind/trap counts from frozen saved responses."""

import json
from pathlib import Path

from analyse import passes_check, score
from common import load_items, load_runs

ROOT = Path(__file__).resolve().parent


def main():
    items = load_items("items.jsonl")
    runs = load_runs("items.jsonl", False, "frozen_20261029")
    heldout = json.loads((ROOT / "analysis_frozen_20261029_heldout/summary-v2.json").read_text())["selected_item_ids"]
    wrong = []
    for model, rows in runs.items():
        for row in rows:
            item = items[row["item"]]
            grade = score(item, row)
            if not grade["correct"]:
                wrong.append(
                    {
                        "model": model,
                        "item": row["item"],
                        "repeat": row["repeat"],
                        "cohort": "heldout" if row["item"] in heldout else "development",
                        "task": row["task"],
                        "errors": grade["errors"],
                        "check_passed": passes_check(item, row, "v2"),
                        "source": item.get("document", item.get("request", item.get("case"))),
                        "gold": item["gold"],
                        "content": row.get("content"),
                        "tool_calls": row.get("tool_calls"),
                    }
                )
    wrong.sort(key=lambda row: (row["item"], row["model"], row["repeat"]))
    out = ROOT / "analysis_frozen_20261029"
    for name, rows in [
        ("all-wrong-answers", wrong),
        ("wrong-accepted-answers", [r for r in wrong if r["check_passed"]]),
    ]:
        (out / (name + ".jsonl")).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )
    for cohort in ["all", "heldout", "development"]:
        folder = out if cohort == "all" else out.with_name(out.name + "_" + cohort)
        summary = json.loads((folder / "summary-v2.json").read_text())
        models = list(summary["models"])
        lines = [
            f"# E06 {cohort}: kind and trap counts, 29 October 2026",
            "",
            "Cells show correct calls / observed calls, followed by distinct items. Repeats are correlated.",
            "",
        ]
        for title, groups in [("Difficulty", summary["kinds"]), ("Named traps", summary["trap_counts"])]:
            lines += [
                "## " + title,
                "",
                "| Group | " + " | ".join(models) + " |",
                "| --- | " + " | ".join("---" for _ in models) + " |",
            ]
            for group, counts in groups.items():
                cells = [
                    f"{counts[m]['correct_calls']}/{counts[m]['n_calls']} ({counts[m]['n_items']} items)"
                    for m in models
                ]
                lines.append("| " + group + " | " + " | ".join(cells) + " |")
            lines.append("")
        (folder / "trap-kind-counts.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Exported {len(wrong)} wrong-response records and three count reports; no new calls.")


if __name__ == "__main__":
    main()
