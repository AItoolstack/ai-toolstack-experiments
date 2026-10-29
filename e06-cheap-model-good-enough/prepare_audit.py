"""Export model-visible requests for a genuinely separate, key-blind audit session."""

import json
from pathlib import Path

from common import load_items, load_tools, messages_for

ROOT = Path(__file__).resolve().parent


def main():
    items = load_items("items.jsonl")
    out = ROOT / "blind-audit-2026-10-29"
    out.mkdir(exist_ok=True)
    with (out / "requests.jsonl").open("w", encoding="utf-8") as f:
        for item in items.values():
            f.write(
                json.dumps({"id": item["id"], "task": item["task"], "messages": messages_for(item)}, ensure_ascii=False)
                + "\n"
            )
    (out / "tools.json").write_text(json.dumps(load_tools(), indent=2) + "\n", encoding="utf-8")
    (out / "INSTRUCTIONS.md").write_text(
        "# Blind audit, stage one\n\n"
        "Read only this folder's INSTRUCTIONS.md, requests.jsonl and tools.json. Do not read parent files, "
        "source code, results, keys, labels, other chats or environment credentials. "
        "All people and policies are fictional.\n\n"
        "Answer every one of the 102 requests using its exact system and user messages. Do not execute any "
        "tool or send anything. For tool items, write the selected action as an object with call (tool name "
        "or null) and args (an object when a tool is selected). Invoice answers use the ten requested keys. "
        "Rules answers use amount and rules_used.\n\n"
        "Save answers.jsonl in this folder, one object per request, with id, answer, ambiguous (boolean), "
        "and reason (one line for any ambiguity). Solve from the supplied text; do not infer an intended key. "
        "Do not invent missing facts. At completion report the number answered and ambiguous IDs. "
        "Label/trap audit is a separate second stage after these answers are saved.\n",
        encoding="utf-8",
    )
    print(f"Exported {len(items)} requests and shared tools into {out.name}; no keys or labels exported.")


if __name__ == "__main__":
    main()
