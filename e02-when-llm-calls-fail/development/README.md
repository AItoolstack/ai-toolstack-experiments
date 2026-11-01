# Development record

The committed pilot uses ten fixed E06 development items, one seed and one replay track.
It tests the design and accounting. It is not evidence for a publication headline.

- `pilot-run/run.json`: exact pilot specification and input hashes.
- `pilot-run/progress.json`: hashes and row counts for the 46 complete compressed shards.
- `pilot-analysis/PILOT-REPORT.md`: readable diagnostic report.
- `pilot-analysis/example.json`: synthetic task, visible outputs and paired recovery traces.
- `pilot-analysis/summary.json`: all scenario/task/policy counts and modelled accounting.
- `pilot-analysis/uncertainty.json`: diagnostic 200-draw paired item intervals.
- `pilot-analysis/verification.json`: all input/run/output hashes and replay verification.

Do not pool scenarios or default variants into a production-rate claim. The original
E06 development/held-out split is preserved; E02 has not created new independent examples.
