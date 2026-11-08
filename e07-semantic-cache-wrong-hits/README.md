# How often does a semantic cache return the wrong answer?

E7 is at its first review milestone, 8 November 2026. Read DESIGN.md for the proposed experiment and development/sample_pairs.tsv for the 30 synthetic near-misses. Each row includes the two questions, both required answers and the reason they differ. Fictional shop, insurance and travel rules apply only to these fixtures.

The sample contains five pairs per failure type. The builder enforces domain and declared template caps, checks repeated numeric-slot wording, rejects duplicate questions and checks that answers differ. A human still needs to review semantic labels and template families.

Run these commands in PowerShell with Python 3.10 or later. This milestone uses the standard library and needs no installation.

```powershell
Set-Location 'E:\AI-ToolStack\Ai_toolstack_expirements\ai-toolstack-experiments\e07-semantic-cache-wrong-hits'
python build_items.py
python build_items.py --check
python run.py --dry-run
python -m unittest -v
```

The generated items_samples.jsonl is deterministic. The dry run overwrites development/dry-run.json with clearly labelled fixture cosine scores. These hashed word-count vectors exercise input validation and scoring. Experimental findings require the two real embedding models after review.

Tej's next review covers DESIGN.md and the sample pairs. The brief requires his yes at this milestone before authoring the full set. The later implementation includes the full corpus, blind audit, cache simulation, resumable model clients, embedding cache, guard, uncertainty analysis and freeze checks. FREEZE.json is created when the audited corpus and model revisions are ready. Final analysis and publication handover follow the measured run.

Review decisions chosen here include a fifth domain to satisfy the diversity caps on five-item groups, an explicit acceptable-answer key for the cache simulation, and reporting useful counts without inventing a usefulness cutoff. These are proposed in DESIGN.md for review.
