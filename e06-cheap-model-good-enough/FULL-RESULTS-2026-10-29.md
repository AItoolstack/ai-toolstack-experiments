# E06 frozen evaluation: results and limits

Run date: **29 October 2026**. All **1,428** expected responses were saved across 102 items.
Report the **81 newly written held-out items** separately from the **21 development examples**.
All comparisons below use the held-out cohort unless explicitly labelled otherwise.
This deliberately difficult synthetic set does not estimate customer production accuracy.

## Four supported findings

1. **The checks caught 2 of 58 incorrect cheap-model responses.** The other 56 passed.
   These are response counts across repeats, spanning 28 model/item pairs and 19 item IDs.
   Original checks caught one; the revised frozen checks caught two. The catches were an
   empty token-capped response and a zero-duration meeting, not semantic source validation.
2. **Agreement improved observed scores at additional cost.** Running three cheap answers
   and escalating disagreement yielded 77–80 correct items out of 81 at $0.40–$0.62 per
   1,000 items. Sol alone scored 79/81 at $1.51. All three cheap calls are charged.
3. **The fallback was not an oracle.** Sol supplied an unsupported due date in `inv36`
   and chose a date instead of asking in `tl35`. Luna's agreement policy exceeded Sol by
   one observed correct item because it kept its correct `inv36` answer rather than escalating.
4. **Frozen-budget failures remain part of the result.** GLM `rl10`, repeat 0, exhausted
   2,000 output tokens without an answer. Tej explicitly approved retaining it as a failure.
   The control returned two native calls once. Neither response was replaced or dropped.

## Alone: responses, distinct items and cost

Each cheap candidate has three responses per item; Sol/control have one. Alone accuracy
averages correctness within item and then over items. Alone cost estimates one production
answer using the mean observed call cost, not all three research repeats.

| Model | Correct responses | Items | Accuracy | USD / 1,000 items |
| --- | --- | --- | --- | --- |
| OSS-20B | 223/243 | 81 | 91.77% | 0.0685 |
| Luna | 235/243 | 81 | 96.71% | 0.0878 |
| GLM Flash | 223/243 | 81 | 91.77% | 0.1305 |
| OSS-120B | 233/243 | 81 | 95.88% | 0.1657 |
| Sol | 79/81 | 81 | 97.53% | 1.5082 |
| GLM temperature-zero control | 76/81 | 81 | 93.83% | 0.1263 |

The differences are small and the task set narrow; do not turn them into a deployment
ranking. The control is outside cascades. One control answer per item does not establish
within-item variation or that the host honoured temperature zero internally.

## Per-task counts

| Model | Invoice: 29 items | Tool: 29 items | Rules: 23 items |
| --- | --- | --- | --- |
| OSS-20B | 87/87 | 73/87 | 63/69 |
| Luna | 87/87 | 81/87 | 67/69 |
| GLM Flash | 80/87 | 82/87 | 61/69 |
| OSS-120B | 87/87 | 77/87 | 69/69 |
| Sol | 28/29 | 28/29 | 23/23 |
| GLM-t0 | 27/29 | 28/29 | 21/23 |

Repeats are correlated. Template-sharing limits what the invoice scores establish.
Free-text tool fields are sometimes graded only for presence. A correct action grade
does not establish accurate email/ticket wording. No business tool executed.

## Cascades

The check policy tests one cheap response and uses Sol when it fails. Its 243 opportunities
retain 81 distinct items. OSS-20B, Luna and OSS-120B never escalated. GLM escalated 2/243,
reaching 225/243 correct at $0.1445 per 1,000, while still accepting 18 wrong responses.

Agreement retains repeat zero when all three frozen answer representations match; otherwise
it uses Sol's repeat zero. Argument/wording differences can trigger escalation. It is not
semantic equivalence or majority voting. The fallback's own sampling variation is unmeasured.

| Cheap candidate + agreement | Correct items | Escalated | USD / 1,000 |
| --- | --- | --- | --- |
| OSS-20B | 79/81 | 10/81 | 0.4033 |
| Luna | 80/81 | 7/81 | 0.4065 |
| GLM Flash | 77/81 | 10/81 | 0.6067 |
| OSS-120B | 79/81 | 5/81 | 0.6193 |

## Paired uncertainty

The deferred analysis plan was recorded before accuracy inspection. Bootstrap 10,000 draws,
seed 6, resampling whole items within task and keeping all repeats and the single Sol answer
together. The primary task mix stays 29/29/23. Use percentile 95% intervals.

Agreement-minus-Sol accuracy differences in percentage points:

- OSS-20B: 0.00, interval −3.70 to +3.70.
- Luna: +1.23, interval 0.00 to +3.70. Its entire observed advantage is one item.
- GLM Flash: −2.47, interval −6.17 to 0.00.
- OSS-120B: 0.00, interval −3.70 to +3.70.

These are conditional item-resampling intervals, not equivalence tests. A zero lower bound
does not establish superiority. They do not capture every dependency among templates and
shared policy documents, or Sol's run-to-run variation. Do not rank near-tied models.

## Worked example chosen by a stated rule

Export every wrong accepted response and sort by item ID, model name and repeat. The first
held-out example is **GLM Flash `inv22`, repeat 0**. Its fictional US invoice states
`03/11/2026`, USD and Net 30. The frozen audited key reads **11 March**, due **10 April**.
GLM returned **3 November**, due **3 December**. The amounts reconcile and both dates are
valid, so the checks accept the internally consistent but source-inconsistent result.

The US context is part of the key convention. Do not turn this into a universal claim about
GLM or imply an arithmetic check can establish a source's date convention. All wrong
accepted responses are available, so the main example does not hide counterexamples.

## Claim-to-source map

| Claim | Evidence |
| --- | --- |
| Complete full coverage | `analysis_frozen_20261029/summary-v2.json`, `coverage` |
| Model/task scores and alone costs | Held-out `summary-v2.json`, `models` |
| Missed 56/58; baseline catches 1 | Held-out summary, sum `checks_by_version` across four candidates |
| Cascade scores, escalations and cost | Held-out summary, `cascades.<model>.all` |
| Intervals and exact method | Held-out `uncertainty.json`, `overall`, `tasks`, `provenance` |
| Every wrong/accepted answer | Full `all-wrong-answers.jsonl`, `wrong-accepted-answers.jsonl` |
| Per-kind/trap counts | Each cohort's `trap-kind-counts.md`, from `kinds` and `trap_counts` |
| Cutoff and two-call events | Raw GLM `rl10` repeat 0 and GLM-t0 `tl03` repeat 0 |
| Health and approved exception | `FULL-RUN-HEALTH-2026-10-29.md` |
| 17 audit changes | `AUDIT-2026-10-29.md`, `audit-review-2026-10-29/audit-resolution.json` |
| Frozen state before inference | `FREEZE.json`, local `e06-frozen` tag at `ffaf7e3` |
| Pre-accuracy bootstrap choices | `ANALYSIS-PLAN-2026-10-29.md` |

Here “held-out” means `analysis_frozen_20261029_heldout/`; “full” means
`analysis_frozen_20261029/`. Raw rows record 29 October 2026, without explicit timezone
offsets. Summary hashes cover inputs, scorer and results; uncertainty adds its source hash.
The frozen scorer still verifies unchanged.

Successful-response tokens imply **$0.311058475** for the full evaluation. This is frozen
list-price accounting, not billing reconciliation. Preflights and earlier development runs
are additional. Every saved evaluation response reports one attempt; no retry logs exist.

## Figure and reproduction

The held-out `figures/e06-cost-accuracy-2026-10-29.png` is 1,320 × 1,360 pixels for
660-pixel display. SVG, actual-number alt text and caption accompany it. It uses Inter and
the requested paper/ink/amber palette. Visual inspection found no clipping or overlapping
labels. Use `python reproduce_full.py`, adding `--figures` after installing optional chart
dependencies. Analysis uses the standard library and makes no API calls. The historical
pilot notebook remains historical; the new script covers the full study.

## Publication status and limits

Everything remains local and unpublished. Public code/data links need checking after Tej
publishes the local results. The article still contains the old pilot body, marked stale;
its rewrite awaits `claude/style-guide.md`. Its §11 checklist has not passed.

Keep these limits near claims: one author, one independent AI auditor, templated invoices,
short fictional policies, a shared prompt per task, different hosts, one Sol/control repeat,
deliberately difficult data, parser leniency, exact agreement representation, partial grading
of free text, conditional item-bootstrap intervals and list-price rather than billed costs.
