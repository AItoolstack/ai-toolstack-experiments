# E06: is the cheap model good enough?

Where does a cheap LLM fail on ordinary production tasks, and can something cheap tell you when to hand the case to a bigger model?

Four cheap models and one expensive model (GPT-6.1 Sol) did three jobs with known right answers:
- pull ten fields from an invoice;
- choose a tool call for an operations assistant, or ask a question when something is missing;
- work out an amount from a one-page written policy.

Every answer is marked by code against a written key. There is no LLM judge, because [E01](../e01-llm-judge-consistency/) showed judges disagree with each other.

Two ways of deciding when to escalate to Sol were compared:
- **Check:** keep the cheap answer unless a code check fails (the JSON parses, the totals add up, the tool exists, its arguments are valid).
- **Agreement:** ask the cheap model three times, and escalate when the three answers differ.

All items are fictional. Nothing comes from an employer or client.

## Result (full run, 29 Oct 2026; 81 held-out items)

| | Correct | Escalated to Sol | USD per 1,000 items |
|---|---|---|---|
| Sol alone | 79/81 | n/a | 1.51 |
| gpt-oss-20b + agreement | 79/81 | 10 | 0.40 |
| GPT-6 Luna + agreement | 80/81 | 7 | 0.41 |
| GLM-5.3-Flash + agreement | 77/81 | 10 | 0.61 |
| gpt-oss-120b + agreement | 79/81 | 5 | 0.62 |

- On their own, the cheap models answered 92–97% of items correctly.
- They gave 58 wrong answers in total, counting all three repeats. The code check caught 2 of them.
- Every agreement cascade ended within two items of Sol. The paired uncertainty intervals against Sol all include zero, so don't rank these models.
- The items are short, synthetic and deliberately tricky. These numbers are not production accuracy. The limits are listed in [FULL-RESULTS](FULL-RESULTS-2026-10-29.md#publication-status-and-limits).

## Where to look

| File or folder | What it is |
|---|---|
| [FULL-RESULTS-2026-10-29.md](FULL-RESULTS-2026-10-29.md) | **Start here.** Findings, counts, uncertainty, worked example, limits, and the source for every claim |
| [DESIGN.md](DESIGN.md), [PROTOCOL.md](PROTOCOL.md) | What was planned before the run, and how it was carried out |
| [AUDIT-2026-10-29.md](AUDIT-2026-10-29.md) | The blind audit of all 102 items, and the 17 items it changed |
| [ANALYSIS-PLAN-2026-10-29.md](ANALYSIS-PLAN-2026-10-29.md) | The uncertainty method, written down before accuracy was looked at |
| [FULL-RUN-HEALTH-2026-10-29.md](FULL-RUN-HEALTH-2026-10-29.md) | Health checks on the run, including the two exceptions that were kept as failures |
| [CHANGELOG.md](CHANGELOG.md) | Every change to the design, with dates and reasons |
| `items.jsonl`, `tools.json`, `policies.py` | The 102 items with their keys, the assistant's 9 tools, and the five written policies with calculators |
| `results_frozen_20261029/` | Every saved model answer (1,428) |
| `analysis_frozen_20261029_heldout/` | The headline cohort: summaries, per-trap counts, uncertainty, every wrong answer, the chart |
| `analysis_frozen_20261029/`, `analysis_frozen_20261029_development/` | The same analysis for all 102 items, and for the 21 development items |
| `analysis_frozen_20261029_heldout/posthoc-2026-10-31.json` | **Exploratory, added after the results were read:** latency, cost at volume, one extra check ("no tool call and no question") |
| `blind-audit-2026-10-29/`, `audit-review-2026-10-29/` | The audit's raw answers and resolutions |
| `FREEZE.json` | Hashes of the items, keys, prompts, code and audit at freeze time (tag `e06-frozen`) |
| `figures-post/` | The three visuals used in the write-up, their generator and `caught_counts.py` (exploratory) |
| `development/` | Pilots and notes from before the freeze. Kept for the record; not part of the result |

**Held-out vs development.** The 21 development items were seen during the pilots, so the headline numbers use only the 81 items written afterwards. The 21 are reported separately.

## Reproduce

The analysis needs only the Python standard library, and makes no API calls:

```text
python freeze.py --check        # items, keys, prompts and code match the freeze
python reproduce_full.py        # re-score every saved answer, bootstrap, export
python analyse_posthoc.py       # exploratory extras
python -m unittest test_e06 test_uncertainty
```

`python reproduce_full.py --figures` also redraws the chart. It needs `pip install -r requirements-dev.txt`.

Expect re-generated numbers to match the committed files except in the last floating-point digit and in line endings.

**Running the models again** costs about $0.31 at list prices. Put your keys in `.env` (see `.env.example`), then run `run-full.ps1 -Stage preflight` followed by `run-full.ps1 -Stage evaluation`, or call `run.py` directly. The models are pinned to the hosts listed in `common.py`.

## Licence
Code: MIT. Items and results: CC BY 4.0. See the [repository README](../README.md).
