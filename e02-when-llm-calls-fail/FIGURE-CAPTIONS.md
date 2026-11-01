# E02 figure captions and alt text

## Recovery flow

A failed primary call enters one of four designs: emit a completed default; retry up to twice
then default; retry once then use fallback; or retry once then explicitly say couldn't check.
A usable response ends recovery early; failed fallback also emits couldn't check.
Policy diagram only, with no measured outcome claim.

## Wrong completed results

Assumed independent 20% timeouts, zero-numeric defaults, 81 reused E06 held-out synthetic items.
Ten seeds and three primary tracks give 2,430 paired replay outcomes per design, not 2,430
independent items. Bars show wrong completed results per 1,000 tasks; intervals are 95%
task-stratified whole-item bootstrap intervals conditional on the saved answers and failure model.

- Default: 578/2430 wrong completed results; 237.86 per 1,000; 95% interval 195.06 to 283.95.
- Retry: 215/2430 wrong completed results; 88.48 per 1,000; 95% interval 39.92 to 141.98.
- Fallback: 194/2430 wrong completed results; 79.84 per 1,000; 95% interval 32.10 to 132.10.
- Say so: 191/2430 wrong completed results; 78.60 per 1,000; 95% interval 31.69 to 130.04.

Unverified tool defaults are excluded from wrong and correct, and reported separately.
Saying couldn't check can withhold correct answers; do not compare these bars without the coverage table.
The close recovery-policy estimates do not establish a ranking. These are not provider failure rates.
Source: analysis/heldout/summary.json and uncertainty.json,
scenarios.independent-20-timeout.zero_numeric.all.<design>.
