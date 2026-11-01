# E02 full results

Status: approved offline evaluation; modelled failure scenarios, not observed provider reliability.

Cohort: development; 21 distinct items; seeds: 10; replay tracks: 3.
Verified 231,840 ledger records by deterministic replay. API calls: 0.

The table below is one specified scenario: independent 20% timeout, zero-numeric defaults.
All 46 scenarios, both variants and task breakdowns are in summary.json.

| Design | Correct | Wrong | Unverified | Couldn't check | Calls | Modelled mean seconds |
| --- | --- | --- | --- | --- | --- | --- |
| default | 458/630 | 164/630 | 8/630 | 0/630 | 630 | 5.985 |
| retry | 549/630 | 81/630 | 0/630 | 0/630 | 765 | 7.767 |
| fallback | 544/630 | 80/630 | 0/630 | 6/630 | 765 | 7.883 |
| say_so | 527/630 | 77/630 | 0/630 | 26/630 | 739 | 7.510 |

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
