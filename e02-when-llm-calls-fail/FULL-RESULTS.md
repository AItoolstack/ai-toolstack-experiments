# E02: what happens when an LLM call fails?

**Completed approved offline evaluation, 1 November 2026.** No API calls or business tools executed.
These are scenario-conditional replay results, not observed production failure rates or provider reliability.

## What was run

The approved E06 OSS-20B -> Sol response pair, unchanged audited synthetic tasks, 46 failure scenarios,
two default variants, ten seeds and three saved primary-response tracks. Retries reuse a saved answer.
The headline uses 81 reused E06 held-out items (29 invoices, 29 tools, 23 rules), not a newly unseen E02 set.
Each design/scenario/variant has 2430 replay outcomes on those 81 distinct items.
894,240 held-out ledger records and 231,840 development ledger records were rebuilt and verified.
Seeds, repeats, failure kinds and scenarios do not create independent items.
The 21 E06 development items are reported separately below. Scripted pilot fixtures are excluded.

## Findings supported by these scenarios

- Under assumed independent 20% timeouts, default showed 578/2430 wrong completed results (237.86 per 1,000); retry showed 215/2430 (88.48 per 1,000). See `claims.json::independent-timeout` for exact file/field/value references.
- In that same scenario, say-so showed 191/2430 wrong results, returned couldn't-check 97/2430 times, and used 2903 calls; fallback showed 194/2430 wrong and 19/2430 couldn't-check results using 3000 calls. See `claims.json::say-so-tradeoff` for exact file/field/value references.
- When a 20% task-level failure episode persisted on primary, retry showed 578/2430 wrong completed results while fallback showed 172/2430; their calls were 3376 and 3376. This tests an assumed persistent episode, not a measured rate-limit storm. See `claims.json::persistent-primary` for exact file/field/value references.
- When the same 20% episode also blocked fallback, fallback and say-so had identical outcome counts: {'correct': 1794, 'couldnt_check': 473, 'unverified': 0, 'wrong': 163}. Fallback used 3376 calls versus 2903 for say-so across 2430 replays. This equality follows the shared-failure model. See `claims.json::shared-failure` for exact file/field/value references.

## No injected failures: the underlying model still makes mistakes

The 0% control has 200/2430 wrong completed responses (82.30 per 1,000).
Every design uses the same first response in this control. Recovery policies only act on detected
failures; say-so cannot intercept an accepted factual mistake. Replaying each saved response across
ten seeds repeats that response rather than supplying ten independent model observations.
Source: `analysis/heldout/summary.json::scenarios.control.zero_numeric.all.default`.

## Independent 20% timeouts

| Design | Correct | Wrong | Unverified | Couldn't check | Wrong / 1,000 (95% item CI) |
| --- | --- | --- | --- | --- | --- |
| Default | 1820/2430 | 578/2430 | 32/2430 | 0/2430 | 237.86 (195.06 to 283.95) |
| Retry | 2215/2430 | 215/2430 | 0/2430 | 0/2430 | 88.48 (39.92 to 141.98) |
| Fallback | 2217/2430 | 194/2430 | 0/2430 | 19/2430 | 79.84 (32.10 to 132.10) |
| Say so | 2142/2430 | 191/2430 | 0/2430 | 97/2430 | 78.60 (31.69 to 130.04) |

Counts have a shared replay denominator, not 2,430 independent examples. Unverified tool no-ops are
excluded from wrong and from correct.
The possible misleading-completion count is [wrong, wrong + unverified].
A numerically correct default still does not establish that a check completed.

| Design | Calls | Calls/task | USD proxy/1,000 | Mean modelled s | Added vs 0% (s) | Modelled p95 s |
| --- | --- | --- | --- | --- | --- | --- |
| Default | 2430 | 1.0000 | 0.05517 to 0.06854 | 6.488 | 5.686 | 30.000 |
| Retry | 3000 | 1.2346 | 0.06805 to 0.08461 | 8.331 | 7.529 | 32.200 |
| Fallback | 3000 | 1.2346 | 0.11556 to 0.14331 | 8.316 | 7.514 | 32.200 |
| Say so | 2903 | 1.1947 | 0.06584 to 0.08191 | 8.000 | 7.198 | 32.200 |

USD ranges are historical token-price scenario proxies, not guarantees about failed-call billing.
Timeout attempts are assumed to take 30s. Means and p95 are modelled, not measured service latency.
Backoff is 1s then 2s. Native saved-response durations proxy healthy attempts.
Source subtree: `analysis/heldout/summary.json::scenarios.independent-20-timeout.zero_numeric.all`.

### Paired differences against default

| Design | Wrong / 1,000 difference (95% paired item CI) | Correct / 1,000 difference (95% paired item CI) |
| --- | --- | --- |
| Retry | -149.38 (-171.19 to -127.57) | 162.55 (142.80 to 182.30) |
| Fallback | -158.02 (-179.84 to -135.80) | 163.37 (144.03 to 183.13) |
| Say so | -159.26 (-180.66 to -137.86) | 132.51 (113.99 to 150.62) |

These 95% percentile intervals use 10,000 task-stratified paired whole-item draws, seed 20261102.
They retain every seed/track within an item. They do not capture template dependence, unmeasured
fallback sampling variation, or uncertainty in the assumed failure/cost/latency/default model.
Do not infer a policy ranking from overlapping marginal intervals; use the paired comparison and context.
Source: `analysis/heldout/uncertainty.json::scenarios.independent-20-timeout.zero_numeric.all.<design>`.

## Persistent primary failures: retries have a limit

| Design | Correct | Wrong | Unverified | Couldn't check | Wrong / 1,000 (95% item CI) |
| --- | --- | --- | --- | --- | --- |
| Default | 1820/2430 | 578/2430 | 32/2430 | 0/2430 | 237.86 (195.06 to 283.95) |
| Retry | 1820/2430 | 578/2430 | 32/2430 | 0/2430 | 237.86 (195.06 to 283.95) |
| Fallback | 2167/2430 | 172/2430 | 0/2430 | 91/2430 | 70.78 (29.63 to 116.05) |
| Say so | 1794/2430 | 163/2430 | 0/2430 | 473/2430 | 67.08 (27.56 to 110.29) |

| Design | Calls | Calls/task | USD proxy/1,000 | Mean modelled s | Added vs 0% (s) | Modelled p95 s |
| --- | --- | --- | --- | --- | --- | --- |
| Default | 2430 | 1.0000 | 0.05517 to 0.06854 | 6.488 | 5.686 | 30.000 |
| Retry | 3376 | 1.3893 | 0.05517 to 0.09529 | 18.751 | 17.949 | 93.000 |
| Fallback | 3376 | 1.3893 | 0.29718 to 0.37988 | 14.046 | 13.244 | 64.620 |
| Say so | 2903 | 1.1947 | 0.05517 to 0.08191 | 12.522 | 11.720 | 61.000 |

A triggered primary episode blocks every primary attempt by construction. An independent fallback
can still fail or answer incorrectly. Extra retries cannot heal an episode defined to outlast the task.

## Shared failures: fallback can add work without changing outcomes

| Design | Correct | Wrong | Unverified | Couldn't check | Wrong / 1,000 (95% item CI) |
| --- | --- | --- | --- | --- | --- |
| Default | 1820/2430 | 578/2430 | 32/2430 | 0/2430 | 237.86 (195.06 to 283.95) |
| Retry | 1820/2430 | 578/2430 | 32/2430 | 0/2430 | 237.86 (195.06 to 283.95) |
| Fallback | 1794/2430 | 163/2430 | 0/2430 | 473/2430 | 67.08 (27.56 to 110.29) |
| Say so | 1794/2430 | 163/2430 | 0/2430 | 473/2430 | 67.08 (27.56 to 110.29) |

| Design | Calls | Calls/task | USD proxy/1,000 | Mean modelled s | Added vs 0% (s) | Modelled p95 s |
| --- | --- | --- | --- | --- | --- | --- |
| Default | 2430 | 1.0000 | 0.05517 to 0.06854 | 6.488 | 5.686 | 30.000 |
| Retry | 3376 | 1.3893 | 0.05517 to 0.09529 | 18.751 | 17.949 | 93.000 |
| Fallback | 3376 | 1.3893 | 0.05517 to 0.37988 | 18.362 | 17.559 | 91.000 |
| Say so | 2903 | 1.1947 | 0.05517 to 0.08191 | 12.522 | 11.720 | 61.000 |

The shared-episode equality of fallback/say-so outcomes is a consequence of the model, not an
empirical discovery about the two historical providers.
This does not model queues or retry-caused congestion.

## All prespecified rates and regimes

The compact table uses timeout and zero-numeric defaults; all five kinds and both variants remain in JSON.

| Regime | Nominal rate | Design | Wrong / replays | Couldn't check / replays | Calls |
| --- | --- | --- | --- | --- | --- |
| independent | 1% | Default | 225/2430 | 0/2430 | 2430 |
| independent | 1% | Retry | 200/2430 | 0/2430 | 2458 |
| independent | 1% | Fallback | 200/2430 | 0/2430 | 2458 |
| independent | 1% | Say so | 200/2430 | 1/2430 | 2457 |
| independent | 5% | Default | 296/2430 | 0/2430 | 2430 |
| independent | 5% | Retry | 200/2430 | 0/2430 | 2568 |
| independent | 5% | Fallback | 199/2430 | 0/2430 | 2568 |
| independent | 5% | Say so | 198/2430 | 13/2430 | 2555 |
| independent | 20% | Default | 578/2430 | 0/2430 | 2430 |
| independent | 20% | Retry | 215/2430 | 0/2430 | 3000 |
| independent | 20% | Fallback | 194/2430 | 19/2430 | 3000 |
| independent | 20% | Say so | 191/2430 | 97/2430 | 2903 |
| persistent_primary | 1% | Default | 225/2430 | 0/2430 | 2430 |
| persistent_primary | 1% | Retry | 225/2430 | 0/2430 | 2484 |
| persistent_primary | 1% | Fallback | 201/2430 | 0/2430 | 2484 |
| persistent_primary | 1% | Say so | 200/2430 | 27/2430 | 2457 |
| persistent_primary | 5% | Default | 296/2430 | 0/2430 | 2430 |
| persistent_primary | 5% | Retry | 296/2430 | 0/2430 | 2680 |
| persistent_primary | 5% | Fallback | 192/2430 | 4/2430 | 2680 |
| persistent_primary | 5% | Say so | 189/2430 | 125/2430 | 2555 |
| persistent_primary | 20% | Default | 578/2430 | 0/2430 | 2430 |
| persistent_primary | 20% | Retry | 578/2430 | 0/2430 | 3376 |
| persistent_primary | 20% | Fallback | 172/2430 | 91/2430 | 3376 |
| persistent_primary | 20% | Say so | 163/2430 | 473/2430 | 2903 |
| persistent_shared | 1% | Default | 225/2430 | 0/2430 | 2430 |
| persistent_shared | 1% | Retry | 225/2430 | 0/2430 | 2484 |
| persistent_shared | 1% | Fallback | 200/2430 | 27/2430 | 2484 |
| persistent_shared | 1% | Say so | 200/2430 | 27/2430 | 2457 |
| persistent_shared | 5% | Default | 296/2430 | 0/2430 | 2430 |
| persistent_shared | 5% | Retry | 296/2430 | 0/2430 | 2680 |
| persistent_shared | 5% | Fallback | 189/2430 | 125/2430 | 2680 |
| persistent_shared | 5% | Say so | 189/2430 | 125/2430 | 2555 |
| persistent_shared | 20% | Default | 578/2430 | 0/2430 | 2430 |
| persistent_shared | 20% | Retry | 578/2430 | 0/2430 | 3376 |
| persistent_shared | 20% | Fallback | 163/2430 | 473/2430 | 3376 |
| persistent_shared | 20% | Say so | 163/2430 | 473/2430 | 2903 |

Independent rates are per-attempt probabilities; persistent rates are per-task episode probabilities.
Realized initial/attempt rates are exported. Each case's seed-level mean min/max is Monte Carlo spread,
not an item confidence interval. Do not average these scenarios into a production failure estimate.

## Failure kinds and default sensitivity

All five injected failure kinds are detectable and share trigger draws and recovery rules. Accordingly,
equal outcome counts across kinds are not five independent confirmations of an accuracy result.
Cost/time differences depend on the prespecified failure proxies (429 0.2s, timeout 30s, cutoff cap).
The null-numeric invoice sensitivity retains its own results; whole-task grading can hide differences
between individual fields of equally wrong default records. Other defaults are outside this comparison.

## Worked example selected by the frozen rule

Selected **inv08**, seed 20261107, track 2, scenario independent-05-timeout. It is the first held-out baseline-correct -> wrong default
at independent 5% timeout, sorted by item ID, seed and track. All qualifying records are in
`analysis/heldout/example-candidates.jsonl`; full task, key, visible replies and source lines are
in `analysis/heldout/example.json`.

| Design | Visible outcome | Calls | Modelled seconds |
| --- | --- | --- | --- |
| Default | wrong | 1 | 30.00 |
| Retry | correct | 2 | 31.44 |
| Fallback | correct | 2 | 31.44 |
| Say so | correct | 2 | 31.44 |

## Separate development cohort

| Design | Correct | Wrong | Unverified | Couldn't check | Wrong / 1,000 (95% item CI) |
| --- | --- | --- | --- | --- | --- |
| Default | 458/630 | 164/630 | 8/630 | 0/630 | 260.32 (169.84 to 363.49) |
| Retry | 549/630 | 81/630 | 0/630 | 0/630 | 128.57 (33.33 to 239.68) |
| Fallback | 544/630 | 80/630 | 0/630 | 6/630 | 126.98 (30.16 to 238.10) |
| Say so | 527/630 | 77/630 | 0/630 | 26/630 | 122.22 (28.57 to 231.75) |

21 development items; 630 replay outcomes per design/scenario/variant; excluded from headline estimates.
Source: `analysis/development/summary.json::scenarios.independent-20-timeout.zero_numeric.all`.

## Limits and publication boundaries

Short synthetic tasks; shared invoice templates and policy text; one primary/fallback pair; one saved
fallback response per item; repeated primary responses reused on retries; coarse grading of tool prose;
assumed defaults, failure probabilities, correlation, durations and failed-call costs; no business execution.
Independent retry improvement follows the failure model. The empirical content is how the saved model
mistakes and task defaults interact with those assumptions. This does not establish production prevalence,
real retry recovery, universal safety, billed cost, queue behaviour or a universally best design.

## Evidence and reproduction

- `FREEZE.json` plus `APPROVAL.json`: exact approved design/input/source hashes and chat approval.
- `results/<cohort>/run.json`, `progress.json`, `shards/`: every schedule, attempt and output reference.
- `analysis/<cohort>/verification.json`: verified ledger counts, inputs and output hashes.
- `analysis/<cohort>/summary.json`, `uncertainty.json`: counts, means and intervals by scenario/task/variant.
- `claims.json`, `RESULTS.md`: exact numerical claim sources, including the outer `scenarios` key.
- `REPORTING.json`: this reporting supplement and its inputs/outputs; approved analytical code is unchanged.
- `README-RESULTS.md`: reader entry point and PowerShell reproduction commands.
