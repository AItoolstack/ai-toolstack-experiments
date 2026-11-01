# E02 handover for the post

Completed 1 November 2026. Do not write a production-failure-rate claim.
Use 81 distinct held-out items; 2,430 is the repeated replay denominator in each scenario.
Development results and scripted diagnostic fixtures stay separate.

## Four supported claims

- Under assumed independent 20% timeouts, default showed 578/2430 wrong completed results (237.86 per 1,000); retry showed 215/2430 (88.48 per 1,000). Exact sources: `RESULTS.md`, section `independent-timeout`, and `claims.json`.
- In that same scenario, say-so showed 191/2430 wrong results, returned couldn't-check 97/2430 times, and used 2903 calls; fallback showed 194/2430 wrong and 19/2430 couldn't-check results using 3000 calls. Exact sources: `RESULTS.md`, section `say-so-tradeoff`, and `claims.json`.
- When a 20% task-level failure episode persisted on primary, retry showed 578/2430 wrong completed results while fallback showed 172/2430; their calls were 3376 and 3376. This tests an assumed persistent episode, not a measured rate-limit storm. Exact sources: `RESULTS.md`, section `persistent-primary`, and `claims.json`.
- When the same 20% episode also blocked fallback, fallback and say-so had identical outcome counts: {'correct': 1794, 'couldnt_check': 473, 'unverified': 0, 'wrong': 163}. Fallback used 3376 calls versus 2903 for say-so across 2430 replays. This equality follows the shared-failure model. Exact sources: `RESULTS.md`, section `shared-failure`, and `claims.json`.

## Concrete example

Use **inv08** from `analysis/heldout/example.json`. The frozen rule selected
the first held-out baseline-correct -> wrong default at independent 5% timeout,
ordered by item, seed and track.
The synthetic source and audited key are in `synthetic_task`; visible replies and source file/line
references are in `paired_designs`. Do not replace this with a more dramatic case.

Audited expected output: `{"amount_due": 244.8, "currency": "GBP", "due_date": "2026-11-01", "gross_total": 244.8, "invoice_date": "2026-10-02", "invoice_number": "AQ-0008", "is_credit_note": false, "net_total": 204.0, "supplier_name": "Alder Quay Workshop 8 Ltd", "tax_total": 40.8}`.

- Default: wrong; 1 calls; 30.00 modelled seconds. Visible response: `{"content": "{\"amount_due\":0,\"currency\":null,\"due_date\":null,\"gross_total\":0,\"invoice_date\":null,\"invoice_number\":null,\"is_credit_note\":false,\"net_total\":0,\"supplier_name\":null,\"tax_total\":0}", "finish_reason": "stop", "tool_calls": []}`
- Retry: correct; 2 calls; 31.44 modelled seconds. Visible response: `{"content": "{\"supplier_name\":\"Alder Quay Workshop 8 Ltd\",\"invoice_number\":\"AQ-0008\",\"invoice_date\":\"2026-10-02\",\"due_date\":\"2026-11-01\",\"currency\":\"GBP\",\"net_total\":204.0,\"tax_total\":40.8,\"gross_total\":244.8,\"amount_due\":244.8,\"is_credit_note\":false}", "finish_reason": "stop", "tool_calls": []}`
- Fallback: correct; 2 calls; 31.44 modelled seconds. Visible response: `{"content": "{\"supplier_name\":\"Alder Quay Workshop 8 Ltd\",\"invoice_number\":\"AQ-0008\",\"invoice_date\":\"2026-10-02\",\"due_date\":\"2026-11-01\",\"currency\":\"GBP\",\"net_total\":204.0,\"tax_total\":40.8,\"gross_total\":244.8,\"amount_due\":244.8,\"is_credit_note\":false}", "finish_reason": "stop", "tool_calls": []}`
- Say so: correct; 2 calls; 31.44 modelled seconds. Visible response: `{"content": "{\"supplier_name\":\"Alder Quay Workshop 8 Ltd\",\"invoice_number\":\"AQ-0008\",\"invoice_date\":\"2026-10-02\",\"due_date\":\"2026-11-01\",\"currency\":\"GBP\",\"net_total\":204.0,\"tax_total\":40.8,\"gross_total\":244.8,\"amount_due\":244.8,\"is_credit_note\":false}", "finish_reason": "stop", "tool_calls": []}`

## What not to claim

- No measured provider failure rates, real retry sampling, live storm/queue behaviour, or billed spend.
- No universal policy winner or proof that a structurally valid response is correct.
- No extra independent examples from the ten seeds, three tracks, five failure kinds or two default variants.
- No claim that an accidentally correct default proves a check completed, or a silent no-op is useful help.
- No hidden ranking from overlapping marginal intervals. Pairwise default comparisons and conditional
  whole-item intervals are in the uncertainty file; templates/failure assumptions remain outside them.

## Figures and reader sources

Use figures-post/e02-recovery-flow.png and e02-wrong-results.png with their captions/metadata.
Use FIGURE-CAPTIONS.md for denominators, intervals, normalization and alt text.
Use root FULL-RESULTS.md and RESULTS.md as the reviewed narrative and exact claim map. Generated
cohort-local report stubs are retained for reproducibility; their shorthand paths omit the outer
`scenarios` JSON key, which the root map and claims.json include explicitly.
This is a handover, not the blog post. All task data is fictional; no employer/client names.
