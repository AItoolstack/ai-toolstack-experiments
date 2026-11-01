# E02 development pilot

Status: DEVELOPMENT ONLY; not a publication result.

Cohort: development_pilot; 10 distinct items; seeds: 1; replay tracks: 1.
Verified 3,680 ledger records by deterministic replay. API calls: 0.

The table below is one specified scenario: independent 20% timeout, zero-numeric defaults.
All 46 scenarios, both variants and task breakdowns are in summary.json.

| Design | Correct | Wrong | Unverified | Couldn't check | Calls | Modelled mean seconds |
| --- | --- | --- | --- | --- | --- | --- |
| default | 10/10 | 0/10 | 0/10 | 0/10 | 10 | 1.271 |
| retry | 10/10 | 0/10 | 0/10 | 0/10 | 10 | 1.271 |
| fallback | 10/10 | 0/10 | 0/10 | 0/10 | 10 | 1.271 |
| say_so | 10/10 | 0/10 | 0/10 | 0/10 | 10 | 1.271 |

Counts reuse the same items and responses. They are not independent trials.
Intervals and paired differences are in uncertainty.json; pilot intervals are diagnostic only.
Cost values are historical token-price proxies; time includes assumed failure durations/backoff.

## Example

No example satisfied the fixed selection rule.

## Limits

Synthetic and partly templated tasks; one reused fallback response; structural detection cannot
establish factual correctness; no-call prose has coarse grading; defaults and failure persistence
are assumptions; no business tools execute; no queues or live provider failures are measured.
Do not present seed repetitions as additional items or cost bounds as invoices.
These failure rates are assumptions, not production measurements.

## Evidence

- summary.json: scenario -> default variant -> task/all -> design; counts, denominator and point metrics.
- uncertainty.json: same paths; item intervals and paired differences, plus method metadata.
- verification.json: exact run, input, review, shard and analysis-code hashes.
- The input run's shards: every attempt and terminal result, source file/line references and accounting.
- example-candidates.jsonl: all examples meeting the primary rule.
- example.json: selected paired trace; pilot-trace-candidates.jsonl: separate development trace candidates.

## Diagnostic coverage

Initial injected-failure records across the paired pilot scenarios: 0.
Scenario records share draws and items; they are not independent observations.
The seed and study scenarios were preserved. Separate forced scripts exercise the failure paths:
see ../scripted-diagnostics/DIAGNOSTICS.md and its paired example.json.
Those scripted fixtures are excluded from the statistical summaries above.
