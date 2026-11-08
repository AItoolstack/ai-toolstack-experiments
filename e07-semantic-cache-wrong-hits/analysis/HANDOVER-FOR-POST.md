# Measured results

Counts refer to distinct pairs. Cache results refer to distinct lookups.

## local

No tested threshold meets the observed near-miss error budget.
Source local.json, safe_threshold and sweep[].pair fields.
Embedding latency is median 70.91259997105226 ms and p95 90.78443494508976 ms over 360 successful first-attempt queries. Source local.json, latency fields.

## Limits

The synthetic cohort has 30 near-miss families with six contextual variants each.
The 120 paraphrases use ten fact families. The 760 cache distractors use twenty frames.
These counts describe this cohort and its traffic mix. Conditional bootstrap intervals cannot establish a population error ceiling.

Opening example follows opening-example.json and items.jsonl. The API run is pending, so opening-example selection is pending.
Read uncertainty.json before comparing models. Avoid production-frequency, universal safety and realised cost-saving claims.
