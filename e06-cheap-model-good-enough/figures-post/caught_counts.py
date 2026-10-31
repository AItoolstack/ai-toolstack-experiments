"""Numbers behind e06-caught-2026-10-31: each cheap model's first answer (repeat 0) on the 81 held-out items.

Uses the frozen scorer and check from analyse.py; makes no API calls. Added 31 Oct 2026, after the results
were read, so it is exploratory in the same sense as analyse_posthoc.py.
    python figures-post/caught_counts.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analyse import answer_key, passes_check, score  # noqa: E402
from common import load_items, read_jsonl  # noqa: E402

items = load_items("items.jsonl")
held = [i for i in items if i not in load_items("items_samples.jsonl")]
total = {"wrong": 0, "check_caught": 0, "agreement_caught": 0, "agreement_escalated_right": 0}
for m in ("oss-20b", "luna", "glm-flash", "oss-120b"):
    rows = {(r["item"], r["repeat"]): r for r in read_jsonl(ROOT / "results_frozen_20261029" / f"{m}.jsonl")}
    for i in held:
        first = rows[(i, 0)]
        escalated = len({answer_key(items[i], rows[(i, k)]) for k in range(3)}) > 1
        if score(items[i], first)["correct"]:
            total["agreement_escalated_right"] += escalated
        else:
            total["wrong"] += 1
            total["check_caught"] += not passes_check(items[i], first)
            total["agreement_caught"] += escalated
print(total)
