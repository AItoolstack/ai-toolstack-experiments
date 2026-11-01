# E02: what happens when an LLM call fails?

An LLM request times out. Does the user see a made-up default, a delayed answer, an answer
from another model, or an honest "couldn't check"? This experiment compares those choices
on the same synthetic invoices, tool-selection requests and written-policy calculations.

**Current status: design and 10-item development pilot for review. No full E02 evaluation
has run.** Pilot numbers are engineering diagnostics, not findings for the post.

We reuse [E06's audited tasks and saved real answers](../e06-cheap-model-good-enough/README.md).
We inject failures and replay four recovery policies. Running E02 makes **zero API calls**,
needs no keys and costs $0 in model usage. Latency and token-price costs are modelled proxies.
No business tools execute. All task data is fictional; no employer or client data is used.

## Start here

| File | Purpose |
| --- | --- |
| [DESIGN.md](DESIGN.md) | Question, hypotheses, defaults, failure model, limits, freeze and review gate |
| [development/pilot-analysis/PILOT-REPORT.md](development/pilot-analysis/PILOT-REPORT.md) | Reviewable 10-item pilot and links to every result |
| [development/scripted-diagnostics/DIAGNOSTICS.md](development/scripted-diagnostics/DIAGNOSTICS.md) | Forced failure paths and concrete paired examples; excluded from statistical results |
| [REVIEW-CHECKLIST.md](REVIEW-CHECKLIST.md) | The concrete decisions to review before a full run |
| [config.json](config.json) | All scenarios, seeds, limits and cohort choices |
| [INPUT-HEALTH.json](INPUT-HEALTH.json) | Coverage and observable health of all 1,428 existing responses |
| [FREEZE.json](FREEZE.json) | Hash-pinned review snapshot, explicitly not evaluation approval |
| `development/pilot-run/` | Complete deterministic, resumable pilot ledger, compressed by scenario |
| `development/scripted-diagnostics/example.json` | Concrete forced traces: task, gold, outputs, attempts and source lines |
| `analysis_e2.py`, `test_e02.py` | Code scoring, whole-item uncertainty and integrity tests |
| `figures-post/make_figures.py` | Flow diagram; charts gated on approved full evaluation |

## What is compared

| Design | On failure | If recovery fails |
| --- | --- | --- |
| Default | no retry | completed default |
| Retry | up to two retries with 1s/2s backoff | completed default |
| Fallback | one retry, then a different saved model response | explicit couldn't-check |
| Say so | one retry | explicit couldn't-check |

The five injected failures are 429, timeout, cutoff, malformed JSON and empty output.
Rates are 1%, 5% and 20%, with independent, persistent-primary and persistent-shared
scenarios plus a 0% control: **46 scenarios**. Numeric-default and null-numeric invoice
variants are kept separate. Every policy gets the same underlying schedule.

The selected primary is E06's OSS-20B response; fallback is E06's Sol response. These are
historical saved records, not current model recommendations. Retries reuse the same saved
answer; they cannot estimate fresh-generation recovery. Persistent scenarios last one task;
they do not simulate queues or measure provider outages.

Report correct, wrong, unverified and couldn't-check outcomes. A silent tool no-op with a
no-call key is unverified, because absence of a call does not prove useful clarification.
Keep that uncertainty visible rather than awarding a free correct answer.

## Reproduce the review milestone (PowerShell, Windows)

From this folder, with Python 3.10 or later:

```powershell
.\run-pilot.ps1
```

Equivalent commands, all offline:

```powershell
python build_items.py --check
python freeze.py --check
python -m unittest test_e02 -v
python run.py --dry-run
python analyse.py
python pilot_fixtures.py
python freeze.py --check
```

`--dry-run` means a 10-item development replay using saved answers, not a live model run.
It produces 3,680 records: 46 scenarios x 10 items x 4 policies x 2 default variants.
It uses one seed/track. Its 200-draw item intervals are diagnostic only.
You can inspect compressed ledgers with Python's built-in `gzip` module.

The fixed ten-item pilot happened to inject **zero failures**, including at 20%. We retained
the seed and archived the original snapshot in `development/initial-pilot/`. An explicit
development amendment adds 600 separate scripted diagnostics to exercise transient,
persistent-primary and shared failures. Read their DIAGNOSTICS.md and example.json to
review what users see. These fixtures never enter the statistical summaries or study rates.

The input builder checks E06's original freeze, coverage, distinct IDs, cohort partition,
tokens, timing and observable faults. It creates an index; it never rewrites E06's tasks.
The runner refuses to resume after configuration, input or review changes, or if a recorded
shard hash changes. Analysis rebuilds and compares every row, so even a tampered ledger
with an updated hash cannot silently change accounting or outcomes.

## After Tej reviews the design and pilot

Do not run this block before that review. The supplied experiment brief requires an
explicit yes after the design and 10-item pilot. No APPROVAL.json is included now.
Recording approval is a human sign-off, not authentication or a security boundary.

```powershell
# Tej runs this only after accepting this exact design/pilot snapshot:
python freeze.py --approve --approved-by Tej --note 'Reviewed DESIGN.md and the 10-item pilot; approved full offline evaluation.'
python run.py --full --cohort heldout
python analyse.py --run results/heldout --out analysis/heldout
python run.py --full --cohort development
python analyse.py --run results/development --out analysis/development
python freeze.py --check
```

The held-out run has 81 distinct items and 894,240 replay records; the separate development
run has 21 distinct items and 231,840 records. Both use ten seeds and three replay tracks.
The full analysis uses 10,000 task-stratified paired item-bootstrap draws and can take
several minutes or longer using only the standard library. Interrupting the runner is safe:
rerun the same command to resume completed, hash-verified shards. Analysis can be rerun.

Each full cohort analysis writes `FULL-RESULTS.md`, `RESULTS.md`, `HANDOVER-FOR-POST.md`,
`summary.json`, `uncertainty.json`, `verification.json` and the selected example and candidates.
Use held-out results for the headline, development results separately. These are reused
E06 cohorts, not a newly unseen E02 test set. Read and review all generated claims before publishing.
The script writes no blog post and does not push or publish anything.

For review changes, first document the reason in DESIGN.md, archive the previous FREEZE.json
under `development/review-history/`, then explicitly create a new snapshot with
`python freeze.py --write`. Use new pilot output paths or archive the old pilot before
rerunning. Never silently replace an approved snapshot; keep approval history with it.

## Figures

Optional dependency: `python -m pip install -r requirements-dev.txt`. The generator reuses
E06's existing Inter font and licence; `--font` can select another local Inter file. It
refuses a silent font substitution.

```powershell
python figures-post/make_figures.py --flow-only
# After approved held-out analysis:
python figures-post/make_figures.py --analysis analysis/heldout
```

The logical canvas is 400 units wide, intended for 480px display, with PNG export at 960px
(2x display size), minimum 15-unit type, the specified palette, SVG companions and captions.
Charts are blocked for pilot data. The flow diagram describes policy choices and needs no results.

## What these results cannot establish

The dataset is synthetic, partly templated and deliberately tricky. The saved fallback has
one response per item. Structural detection misses plausible factual mistakes. Some tool
prose is graded coarsely. Costs are historical token-price proxies, not billed spend;
failure durations, rates and persistence are assumed. No production rate, retry sampling,
congestion, business side effect or universal best recovery design is measured.

The numerical effect of independent retries follows the failure model by construction.
The useful empirical comparison is how those assumptions interact with the saved model
errors, task defaults and fallback behaviour. Keep both parts visible.

Code: repository MIT licence. Tasks and saved results retain the repository's CC BY 4.0 terms.
