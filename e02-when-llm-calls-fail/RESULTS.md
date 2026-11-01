# E02 claim-to-source map

All claims are conditional on the stated scenario.

## independent-timeout

Under assumed independent 20% timeouts, default showed 578/2430 wrong completed results (237.86 per 1,000); retry showed 215/2430 (88.48 per 1,000).

- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.default.counts.wrong` = `578`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.default.denominator_replays` = `2430`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.default.point.wrong_per_1000` = `237.86008230452674`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.retry.counts.wrong` = `215`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.retry.denominator_replays` = `2430`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.retry.point.wrong_per_1000` = `88.47736625514402`

## say-so-tradeoff

In that same scenario, say-so showed 191/2430 wrong results, returned couldn't-check 97/2430 times, and used 2903 calls; fallback showed 194/2430 wrong and 19/2430 couldn't-check results using 3000 calls.

- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.say_so.counts.wrong` = `191`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.say_so.counts.couldnt_check` = `97`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.say_so.total_calls` = `2903`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.say_so.denominator_replays` = `2430`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.fallback.counts.wrong` = `194`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.fallback.counts.couldnt_check` = `19`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.fallback.total_calls` = `3000`
- `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all.fallback.denominator_replays` = `2430`

## persistent-primary

When a 20% task-level failure episode persisted on primary, retry showed 578/2430 wrong completed results while fallback showed 172/2430; their calls were 3376 and 3376. This tests an assumed persistent episode, not a measured rate-limit storm.

- `analysis/heldout/summary.json::scenarios.persistent_primary-20-timeout.zero_numeric.all.retry.counts.wrong` = `578`
- `analysis/heldout/summary.json::scenarios.persistent_primary-20-timeout.zero_numeric.all.retry.total_calls` = `3376`
- `analysis/heldout/summary.json::scenarios.persistent_primary-20-timeout.zero_numeric.all.retry.denominator_replays` = `2430`
- `analysis/heldout/summary.json::scenarios.persistent_primary-20-timeout.zero_numeric.all.fallback.counts.wrong` = `172`
- `analysis/heldout/summary.json::scenarios.persistent_primary-20-timeout.zero_numeric.all.fallback.total_calls` = `3376`
- `analysis/heldout/summary.json::scenarios.persistent_primary-20-timeout.zero_numeric.all.fallback.denominator_replays` = `2430`

## shared-failure

When the same 20% episode also blocked fallback, fallback and say-so had identical outcome counts: {'correct': 1794, 'couldnt_check': 473, 'unverified': 0, 'wrong': 163}. Fallback used 3376 calls versus 2903 for say-so across 2430 replays. This equality follows the shared-failure model.

- `analysis/heldout/summary.json::scenarios.persistent_shared-20-timeout.zero_numeric.all.fallback.counts` = `{"correct": 1794, "couldnt_check": 473, "unverified": 0, "wrong": 163}`
- `analysis/heldout/summary.json::scenarios.persistent_shared-20-timeout.zero_numeric.all.fallback.total_calls` = `3376`
- `analysis/heldout/summary.json::scenarios.persistent_shared-20-timeout.zero_numeric.all.fallback.denominator_replays` = `2430`
- `analysis/heldout/summary.json::scenarios.persistent_shared-20-timeout.zero_numeric.all.say_so.counts` = `{"correct": 1794, "couldnt_check": 473, "unverified": 0, "wrong": 163}`
- `analysis/heldout/summary.json::scenarios.persistent_shared-20-timeout.zero_numeric.all.say_so.total_calls` = `2903`
- `analysis/heldout/summary.json::scenarios.persistent_shared-20-timeout.zero_numeric.all.say_so.denominator_replays` = `2430`
