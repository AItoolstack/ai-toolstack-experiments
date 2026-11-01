# Handover for the post

Do not pool scenarios into a production claim.

The following preselected comparison uses independent 20% timeout and zero-numeric defaults.

- default: 578/2430 wrong completed results; 0/2430 couldn't-check results; 2430 calls. Source: `summary.json::independent-20-timeout.zero_numeric.all.default`; read matching uncertainty.json before comparing.
- retry: 215/2430 wrong completed results; 0/2430 couldn't-check results; 3000 calls. Source: `summary.json::independent-20-timeout.zero_numeric.all.retry`; read matching uncertainty.json before comparing.
- fallback: 194/2430 wrong completed results; 19/2430 couldn't-check results; 3000 calls. Source: `summary.json::independent-20-timeout.zero_numeric.all.fallback`; read matching uncertainty.json before comparing.
- say_so: 191/2430 wrong completed results; 97/2430 couldn't-check results; 2903 calls. Source: `summary.json::independent-20-timeout.zero_numeric.all.say_so`; read matching uncertainty.json before comparing.

## Example rule

First baseline-correct -> wrong default at independent 5% timeout, ordered item, seed, track.
See example-candidates.jsonl and example.json. If none qualify, do not substitute a dramatic case.

## What not to claim

No measured production failure rates, real retry recovery, queue congestion, provider billing,
universal best policy, or proof that structural checks establish truth. Report unverified tool defaults.
Read DESIGN.md and FULL-RESULTS.md limits; manually review every publication claim.
