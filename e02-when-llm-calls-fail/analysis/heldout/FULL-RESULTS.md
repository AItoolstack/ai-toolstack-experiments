# E02 full results

Status: approved offline evaluation; modelled failure scenarios, not observed provider reliability.

Cohort: heldout; 81 distinct items; seeds: 10; replay tracks: 3.
Verified 894,240 ledger records by deterministic replay. API calls: 0.

The table below is one specified scenario: independent 20% timeout, zero-numeric defaults.
All 46 scenarios, both variants and task breakdowns are in summary.json.

| Design | Correct | Wrong | Unverified | Couldn't check | Calls | Modelled mean seconds |
| --- | --- | --- | --- | --- | --- | --- |
| default | 1820/2430 | 578/2430 | 32/2430 | 0/2430 | 2430 | 6.488 |
| retry | 2215/2430 | 215/2430 | 0/2430 | 0/2430 | 3000 | 8.331 |
| fallback | 2217/2430 | 194/2430 | 0/2430 | 19/2430 | 3000 | 8.316 |
| say_so | 2142/2430 | 191/2430 | 0/2430 | 97/2430 | 2903 | 8.000 |

Counts reuse the same items and responses. They are not independent trials.
Intervals and paired differences are in uncertainty.json; pilot intervals are diagnostic only.
Cost values are historical token-price proxies; time includes assumed failure durations/backoff.

## Example

Selected item: inv08; see example.json for source lines, visible outputs and all four paired designs.

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
