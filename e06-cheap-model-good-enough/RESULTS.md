# E06 evidence map — development pilot, 29 October 2026

The full evaluation has not run. The following figures describe only the six-model pilot
against the preserved development key. Audit is complete and evaluation-copy key changes
are logged in `AUDIT-2026-10-29.md`; these figures still use the historical pilot key. They are
provisional development observations, not final rankings or production accuracy estimates.

## Claims and supporting files

| Observation | Evidence |
| --- | --- |
| 126 answers, 21 per model, one repeat | `analysis_samples_sixmodel_20261029/summary-v2.json`, `coverage` |
| OSS-20B 18/21; Luna 19/21; GLM 19/21; OSS-120B 18/21; Sol 21/21; GLM-t0 19/21 | Same summary, `models.<model>.all.accuracy` and `.n` |
| All 10 incorrect answers from the four cheap cascade candidates passed the v2 checks | Same summary, `checks_by_version` for OSS-20B (3), Luna (2), GLM (2), OSS-120B (3); `wrong_caught` is zero in each |
| The control's two incorrect answers also passed; it is outside the cascades | Same summary, `checks_by_version.glm-flash-t0.v2.all`, and absence from `cascades` |
| No check cascade escalated in this pilot | Same summary, `cascades.<cheap>.all.check.escalated` is zero |
| Agreement cascade is not measurable from one repeat | Same summary, `cascades.<cheap>.all.agreement.status` is `incomplete` |
| OSS-20B claimed ticket creation without a native call | `results_samples_sixmodel_20261029/oss-20b.jsonl`, item `tl03`, repeat 0; normalized native calls are empty |
| Projected 102-item evaluation: 1,428 calls, $0.33168 at observed token lengths, $0.46784 at double output | `analysis_samples_sixmodel_20261029/pilot-health-2026-10-29.json`, `study_projection` |
| Pilot-only estimated successful-call token cost: $0.0470399 | Same health JSON, `saved_call_estimated_usd` |

All raw pilot rows have recorded dates of 29 October 2026. Timestamps lack explicit offsets.
Summary provenance contains dataset, scorer and result-file hashes. Prices are configured
list prices, with public study-model verification recorded in `RESUME-2026-10-29.md`.
Costs are not billing reconciliation and omit prior development spend.

## Interpretation limits

Seven items per task and one observation per item are insufficient for close model rankings.
Sol's 21/21 does not establish reliability in a customer workflow. The item set deliberately
overrepresents difficult cases. Identical prompts do not establish equal prompt suitability.
The prose-ticket failure cannot be assigned confidently to weights versus host parsing from
the normalized row alone. Fenced JSON is accepted by the existing parser. Schema validity
does not establish source support or the right first action.

The added evaluation items were authored after these development pilots. If the full 102
includes the 21 development examples, report the 81 newly written examples separately.
The final article and figures must be updated after audit and the full evaluation. Nothing
in this file authorizes publishing the current pilot as the completed study.
