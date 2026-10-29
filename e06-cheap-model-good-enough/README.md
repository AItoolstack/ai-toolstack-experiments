# E06: can simple checks make cheap AI reliable?

I give models three jobs: extract an invoice, choose an operations tool, and calculate an amount
from a written policy. Code compares each answer with a written key. Then I test whether cheap
checks can tell us which answers need a larger model.

**Resumption, 29 October 2026:** Tej selected the six-model handover lineup. See
[the resumption report](RESUME-2026-10-29.md) for pilot health, request changes, validation,
owner-run commands and earlier development history. The six-model pilot is now complete;
see [its health review](PILOT-REVIEW-2026-10-29.md).
`run-pilot.ps1` separates the paid preflight and pilot stages; each pilot model runs once
per item. The historical three-model results below remain development evidence.

**Completed evaluation, 29 October 2026:** all 1,428 responses are saved. See
[the results](RESULTS.md), [full analysis](FULL-RESULTS-2026-10-29.md) and
[health exceptions](FULL-RUN-HEALTH-2026-10-29.md). The audited set was frozen before
evaluation. Report the 81 held-out items separately from the 21 development examples.

Reproduce full saved-result analysis without credentials or inference:

```text
python reproduce_full.py
python reproduce_full.py --figures
```

The second command needs optional chart dependencies from requirements-dev.txt. The
historical pilot notebook and results below remain preserved. Nothing has been published.

**Status, 25 October 2026: development pilot only.** The revised pilot has 21 synthetic items,
one repeat each, across three models. The planned 102-item evaluation has not been built or run.
These samples have now informed development; they are not an unseen evaluation set.

## Revised pilot: whole answers correct

| Model | Invoice | Tool calling | Policy rules | Total |
| --- | --- | --- | --- | --- |
| llama-8b | 5/7 | 2/7 | 2/7 | 9/21 |
| oss-20b | 7/7 | 7/7 | 6/7 | 20/21 |
| sol | 7/7 | 7/7 | 7/7 | 21/21 |

Both the original checks and the revised checks accepted all 12 incorrect Llama answers and the
one incorrect OSS answer in this run. All answers passed, so the check cascade never escalated.
The three-repeat agreement cascade is unavailable: one answer does not establish agreement.
Seven examples per task are too few for model rankings or claims about production reliability.

The original pilot is kept in `results_samples/`: 21 Llama rows, 21 OSS rows and 7 Sol invoice rows.
Sol's original Chat Completions tool request failed with HTTP 400. The revised run uses Responses
for all OpenAI tasks, keeping low reasoning effort and best-effort tools. It is a separate run,
not a repair of the old answers. No change in accuracy is attributed to the API adapter.

## Reproduce the numbers (no keys or network needed)

From this folder, Python 3.10 or later:

```text
python analyse.py --items items_samples.jsonl --repeats 1 --run-tag v2
python analyse.py --items items_samples.jsonl --repeats 1 --run-tag v2 --checks baseline
python analyse.py --items items_samples.jsonl --repeats 1
python -m unittest -v test_e06.py
```

The runner, analysis and regression tests use only the standard library. To reproduce charts:

```text
python -m pip install -r requirements-dev.txt
python make_figures.py --summary analysis_samples_v2/summary-v2.json
```

`reproduce.ipynb` runs the saved-results analysis and charts. It makes no API calls.

## Run it yourself

Keys come from the environment or a local `.env`. Never add `.env` to version control. Run one
preflight per model to check each task's API contract before the main run:

```text
python run.py --model llama-8b --items items_samples.jsonl --repeats 1 --workers 4 --run-tag v2 --preflight
python run.py --model oss-20b --items items_samples.jsonl --repeats 1 --workers 4 --run-tag v2 --preflight
python run.py --model sol --items items_samples.jsonl --repeats 1 --workers 4 --run-tag v2 --preflight
python run.py --model llama-8b --items items_samples.jsonl --repeats 1 --workers 4 --run-tag v2
python run.py --model oss-20b --items items_samples.jsonl --repeats 1 --workers 4 --run-tag v2
python run.py --model sol --items items_samples.jsonl --repeats 1 --workers 4 --run-tag v2
```

Preflights are paid calls stored in `results_samples_v2_preflight/`; they are excluded from
the scored pilot. Same-command reruns skip saved answers. A configuration fingerprint prevents
appending to legacy or incompatible results. Choose a new tag after a request change. Do not
run the same model and tag in two terminals at once.

`--dry-run` saves scripted answers to separate `results-dry*` folders without keys or network.
The full three-repeat run defaults to `items.jsonl`, which does not exist yet. Do not regenerate
or change the sample items or answer key as part of infrastructure work.

## What is measured

- Whole-answer accuracy, unique item counts, and individual field/argument errors.
- Original and revised checks: wrong answers caught, wrong answers accepted, correct answers
  unnecessarily escalated, escalation rate, and accuracy among accepted answers.
- Check cascades on complete matching cohorts, separately by task and overall. Agreement needs
  cheap repeats 0, 1 and 2 for every item plus the fallback's repeat 0. Missing coverage produces
  an explicit incomplete result, not an estimate on a convenient subset.
- Listed token cost per 1,000 items and median response latency. Failed attempts have unknown
  billed cost; discounts are not modelled. Revised latency includes retries. Cascade latency
  is an estimate for sequential execution, not a measured workflow.
- Row-level diagnostics: cutoff, unreadable JSON or amounts, malformed arguments, multiple
  calls, detected tool JSON returned as text, and possible prose calls for manual review.

Tool grading checks schema shape and types as well as the answer key. Some free-text arguments
are graded only for presence. A correct grade therefore does not establish that their wording
is accurate. A no-call answer is graded as an action choice; the quality of its question is not
semantically judged. Text-call detection is heuristic, not a complete natural-language parser.

## Files and evidence

| File/folder | Purpose |
| --- | --- |
| `DESIGN.md` | Original design, with a dated amendment pointing to the revised protocol |
| `PROTOCOL.md` | Current measurement rules and gates before an unseen evaluation |
| `CHANGELOG.md` | Changes, pilot observations, validation and remaining work |
| `run.py`, `common.py` | Calls, normalized answers, configuration fingerprints and result loading |
| `analyse.py` | Scoring, validator metrics, coverage checks, cascades and row audit |
| `test_e06.py` | Offline regression checks for meaningful failure cases |
| `results_samples/` | Original pilot, preserved |
| `results_samples_v2/` | Revised pilot, 63 saved answers |
| `results_samples_v2_preflight/` | Nine separate compatibility probes |
| `analysis_samples*/` | Summaries and row audits derived from saved answers |
| `make_figures.py`, `reproduce.ipynb` | Charts and reproducible saved-results walkthrough |
| `PUBLICATION.md` | Link to the canonical article draft in the site workspace |

No item or answer key was changed during this revision. The label audit and unseen-set freeze
remain prerequisites for the full evaluation. See `PROTOCOL.md` before adding more runs.
