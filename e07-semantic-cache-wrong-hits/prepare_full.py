"""Build and validate the full candidate cohort and a label-free audit packet."""
import json
import random

from build_items import HERE
from corpus import cache_entries, full_items, validate_full


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8")


def main():
    items = full_items()
    validate_full(items)
    cache = cache_entries(items)
    write_jsonl(HERE / "items.jsonl", items)
    write_jsonl(HERE / "cache.jsonl", cache)
    rng = random.Random(7007)
    selected = []
    for group in sorted({item["type"] for item in items}):
        count = 12 if group in ("paraphrase", "unrelated") else 8
        selected.extend(rng.sample([item for item in items if item["type"] == group], count))
    rng.shuffle(selected)
    packet, key = [], []
    for index, item in enumerate(selected):
        texts = [item["source"], item["query"]]
        rng.shuffle(texts)
        ident = f"audit-{index:03d}"
        packet.append(dict(id=ident, left=texts[0], right=texts[1]))
        key.append(dict(id=ident, item=item["id"], expected=item["label"]))
    write_jsonl(HERE / "development/blind-packet.jsonl", packet)
    write_jsonl(HERE / "development/audit-key.jsonl", key)
    print(f"Validated {len(items)} pairs, {len(cache)} cache entries and {len(packet)} blind audit pairs.")


if __name__ == "__main__":
    main()
