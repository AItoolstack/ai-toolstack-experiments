# Review and pilot material

sample_pairs.tsv is the authored review source. build_items.py creates ../items_samples.jsonl from it.

dry-run.json records the offline wiring check and its input SHA-256. Its fixture scores have no experimental interpretation. Re-running the same input gives identical output.

No real-model pilot has run. Review changes and audit disagreements will be recorded in ../DESIGN.md before freezing. Later exploratory outputs belong here and must state when their rules were chosen.
