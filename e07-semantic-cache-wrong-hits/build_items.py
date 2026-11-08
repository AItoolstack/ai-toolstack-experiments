"""Build the review cohort without importing any embedding client."""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TYPES = (
    "entity_id", "negation", "number_date", "scope_qualifier",
    "direction_word_order", "actor_permission",
)
FIELDS = ("type", "domain", "template", "source", "query", "source_answer", "query_answer", "why")


def validate(items):
    if len(items) != 30 or Counter(item["type"] for item in items) != Counter(dict.fromkeys(TYPES, 5)):
        raise ValueError("Review cohort requires five items of each near-miss type.")
    seen_ids = set()
    seen_texts = set()
    groups = defaultdict(list)
    for item in items:
        if any(not isinstance(item.get(field), str) or not item[field].strip() for field in FIELDS):
            raise ValueError("Every item needs complete text, answers and provenance fields.")
        if item["id"] in seen_ids:
            raise ValueError("Duplicate item ID.")
        seen_ids.add(item["id"])
        if item["source_answer"].strip().casefold() == item["query_answer"].strip().casefold():
            raise ValueError("A near-miss requires different answers.")
        for field in ("source", "query"):
            text = item[field].strip().casefold()
            if text in seen_texts:
                raise ValueError("Duplicate question text.")
            seen_texts.add(text)
        groups[item["type"]].append(item)
    for group in groups.values():
        for field, cap in (("domain", 0.35), ("template", 0.25)):
            if max(Counter(item[field] for item in group).values()) > len(group) * cap:
                raise ValueError(f"{field} exceeds its diversity cap.")
        frames = Counter(re.sub(r"\d+", "#", item["source"].casefold()) for item in group)
        if max(frames.values()) > len(group) * 0.25:
            raise ValueError("Repeated numeric-slot wording exceeds the template cap.")


def build():
    with (HERE / "development/sample_pairs.tsv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    for index, item in enumerate(rows, 1):
        item.update(id=f"review-{index:03d}", label="different", provenance="synthetic")
    validate(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the generated file matches its source.")
    parser.add_argument("--full", action="store_true", help="Build or check the complete candidate cohort.")
    args = parser.parse_args()
    if args.full:
        from corpus import cache_entries, full_items, validate_full
        rows = full_items()
        validate_full(rows)
        cache = cache_entries(rows)
        for name, data in (("items.jsonl", rows), ("cache.jsonl", cache)):
            content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in data)
            target = HERE / name
            if args.check:
                if not target.exists() or target.read_text(encoding="utf-8") != content:
                    raise SystemExit(f"{name} differs from its authored inputs.")
            else:
                target.write_text(content, encoding="utf-8")
        print("Validated 360 distinct pairs and 1,000 distinct stored questions.")
        return
    content = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in build())
    target = HERE / "items_samples.jsonl"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            raise SystemExit("Sample file differs. Run build_items.py.")
    else:
        target.write_text(content, encoding="utf-8")
    print("Validated 30 distinct synthetic pairs, five per near-miss type.")


if __name__ == "__main__":
    main()
