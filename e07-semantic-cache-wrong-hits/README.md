# How often does a semantic cache return the wrong answer?

**Write-up:** [My cache found a 0.997 match. It answered the opposite request.](https://www.ai-toolstack.com/blog/semantic-cache-wrong-answer/) (from 18 Nov 2026). New to semantic caching? Start with [Semantic caching, explained](https://www.ai-toolstack.com/blog/semantic-caching-explained/).

## Results (measured 8 Nov 2026)

- 360 synthetic question pairs (120 rewordings, 180 near-misses, 60 unrelated) and a 1,000-entry cache, scored with OpenAI `text-embedding-3-small` (API) and `all-MiniLM-L6-v2` (local) at every cutoff from 0.80 to 0.99.
- No cutoff met the error budget set before the run (at most 2 of 180 near-misses through), for either model.
- At 0.99 every useful cache reply was gone and 8 wrong ones remained, all swapped directions.
- A simple check on IDs, numbers, dates and negation removed those kinds of wrong matches without losing a useful one. Swapped roles, changed scope and a different person acting still got through.
- Numbers: `analysis/FULL-RESULTS.md`, `analysis/local.json`, `analysis/api.json`, `analysis/uncertainty.json`. Labels were checked by a blind AI audit of 72 pairs (`development/AUDIT.md`), not by a person.

The notes below are the working record from the design and run stages.

E7's design milestone was approved on 8 November 2026. The full candidate corpus contains 360 synthetic pairs and a 1,000-entry cache. Read DESIGN.md for the protocol, construction choices and limitations. Fictional shop, insurance and travel rules apply only to these fixtures.

The sample contains five pairs per failure type. The builder enforces domain and declared template caps, checks repeated numeric-slot wording, rejects duplicate questions and checks that answers differ. The design was approved after a 30-item sample, and a blind AI audit checked 72 labels before the measured runs (see DESIGN.md and development/AUDIT.md).

Run these commands in PowerShell with Python 3.10 or later. This milestone uses the standard library and needs no installation.

```powershell
Set-Location 'E:\AI-ToolStack\Ai_toolstack_expirements\ai-toolstack-experiments\e07-semantic-cache-wrong-hits'
python build_items.py
python build_items.py --check
python run.py --dry-run
python -m unittest -v
```

The generated items_samples.jsonl is deterministic. The dry run overwrites development/dry-run.json with clearly labelled fixture cosine scores. These hashed word-count vectors exercise input validation and scoring. The measured results come from the two real embedding models, not from these fixture scores.

The full cohort uses 30 near-miss families with six contextual variants each, ten fact families for paraphrases, and those ten topics for unrelated pairs. Its 760 distractors use twenty question frames. Domain and template caps pass, but contextual variants are correlated. Read both the item-bootstrap and family-bootstrap intervals before drawing conclusions. The independent AI audit agreed with all 72 sampled labels. It cannot certify all labels or all cache equivalences.

## Full experiment commands

Run from this folder in PowerShell. Only the API command incurs provider charges. Tej runs it locally. The free local model downloads weights on first use. requirements.txt installs model dependencies. FREEZE.json records exact runtime versions and an immutable local weights revision.

```powershell
python -m pip install -r requirements.txt
python prepare_full.py
python -m unittest -v
python run.py --full --dry-run
python analyse.py --dry-run
python analyse_uncertainty.py --dry-run --replicates 100
python freeze.py --check
python run.py --full --model local
python analyse.py --models local
python run.py --estimate
```

Keep audit records intact when regenerating the candidate set. If the frozen corpus or software changes, the real runner stops. Record an amendment before creating a new freeze or seeing any changed scores. A first freeze can be created with `python freeze.py --revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41` after the audit and runtime installation.

Tej's API command and subsequent analysis commands are in RUN-PAID.ps1. The cost estimate based on the current input byte count is under $0.005 including a second-pass allowance at the assumed $0.02 per million tokens. The command prints the current input estimate before executing. Recheck pricing before a later run.

The runner resumes missing embeddings and retains the original timings for completed ones. Concurrent writers are blocked by .run.lock, which contains the writer PID. After a killed process, confirm that PID has exited before removing the stale lock. An interrupted API request may have been billed even if no response was saved. Failure records contain input hashes. Query latency summaries exclude inputs with recorded failed attempts and report their count.

Measured vectors live in ignored results/ folders. Analysis writes FULL-RESULTS.md, RESULTS.md, HANDOVER-FOR-POST.md, opening-example.json, figures-data/ and uncertainty.json under analysis/. Fixture outputs live in development/full-fixture/, labelled fixture-only. Send back both real model results folders and the analysis folder, including manifests, embeddings.json and failures.json if present. Keys stay in the ignored .env or environment.

Review decisions chosen here include a fifth domain to satisfy the diversity caps on five-item groups, an explicit acceptable-answer key for the cache simulation, and reporting useful counts without inventing a usefulness cutoff. These are proposed in DESIGN.md for review.
