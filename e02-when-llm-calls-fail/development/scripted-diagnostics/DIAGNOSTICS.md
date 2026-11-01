# Scripted failure diagnostics

Development fixtures only. These scripts force failures; no probability or confidence claim is made.
The unchanged probabilistic pilot happened to trigger zero failures. Its seed was not changed.
These 600 separate records exercise three explicit schedules across all five failure types and ten
development items. They never enter summary.json, uncertainty.json or publication results.

The concrete example is fixed: inv01, timeout, primary track 0.
Source references and visible outputs are in example.json.

| Script | Design | Outcome | Calls | Modelled seconds |
| --- | --- | --- | --- | --- |
| first_primary_only | default | wrong | 1 | 30.00 |
| first_primary_only | retry | correct | 2 | 31.95 |
| first_primary_only | fallback | correct | 2 | 31.95 |
| first_primary_only | say_so | correct | 2 | 31.95 |
| all_primary | default | wrong | 1 | 30.00 |
| all_primary | retry | wrong | 3 | 93.00 |
| all_primary | fallback | correct | 3 | 63.22 |
| all_primary | say_so | couldnt_check | 2 | 61.00 |
| all_calls | default | wrong | 1 | 30.00 |
| all_calls | retry | wrong | 3 | 93.00 |
| all_calls | fallback | couldnt_check | 3 | 91.00 |
| all_calls | say_so | couldnt_check | 2 | 61.00 |

first_primary_only: initial primary call fails; all subsequent calls are healthy.
all_primary: primary stays failed; fallback is healthy.
all_calls: primary and fallback both stay failed.

Healthy means no injected failure; the saved answer can still be wrong.
