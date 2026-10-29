# Six-model pilot health review: 29 October 2026

**Outcome: proceed to item construction and blind audit.** All 126 expected calls were
saved, 21 per model, one repeat each. Run dates are 29 October 2026 as recorded; raw
timestamps lack an explicit UTC offset. This is development data, not the full evaluation.

Source folder: `results_samples_sixmodel_20261029/`. The reproducible health report, raw-file
hashes and by-task token means are in
`analysis_samples_sixmodel_20261029/pilot-health-2026-10-29.json`.

## Health checklist

1. **PASS, with format caveat — parseability.** No unreadable invoice JSON or rules amounts.
   Fenced JSON occurs in OSS-20B and both GLM arms and is accepted by the existing parser.
   This is not evidence of strict JSON-only compliance. No prompt or parser change is made.
2. **PASS — completeness.** No cutoff or incomplete responses. Largest outputs by model:
   OSS-20B 226, Luna 240, GLM 160, OSS-120B 309, Sol 117, GLM-t0 158. All are below 2,000.
3. **PASS WITH MANUAL FINDING — tool transport.** No structurally detected JSON tool call
   returned as text or malformed/multiple native calls. Manual review found OSS-20B `tl03`
   claiming to have created a Finance ticket in prose, with no native call. Retain this
   as a workflow failure. The existing structural detector misses this prose example.
   The saved normalized response has no upstream parser telemetry, so attribution between
   model output and host parsing is unresolved. Do not blame model weights alone or rerun
   it away. Its grade remains the existing no-call-when-a-call-is-required failure.
4. **PASS — hosts and configuration.** All OSS responses report Groq, all GLM responses
   Z.AI, and all OpenAI responses OpenAI. All saved request fingerprints match current
   request construction. Every expected item/repeat appears exactly once.
5. **PASS — token accounting.** All 126 rows report input, output and reasoning tokens.
   Zero reasoning tokens is retained as reported. Costs include completion tokens once;
   reasoning tokens are not added again. All calls report one attempt; no retry errors
   or separate model error logs are present.
6. **PASS WITH FINDINGS — manual prompt review.** Reviewed `inv01`–`inv03`, `tl01`–`tl03`
   and `rl01`–`rl03` for each of six models: 54 answers. No shared prompt or format defect
   warrants a change. Wrong tools, missed thresholds, and omitted invoice values remain
   observations for scoring and the independent key audit. No model-specific prompt tuning.
7. **PASS — budget gate.** Using task-specific measured token means and the selected
   3/3/3/3/1/1 schedule, 102 items imply **1,428 calls**, approximately **$0.33168** total:
   OpenAI $0.19620, OpenRouter $0.13548. With twice the measured output tokens, total
   projection is **$0.46784**. This is below the $3 stop threshold. New policies may change
   prompt length; recalculate after the set exists. These are list-price projections,
   not billing reconciliation, and exclude earlier development runs.

The pilot itself implies $0.0470399 from saved token usage. The separate six-model preflight
implies $0.006318175, giving $0.053358075 for these two stages. Previous development pilots
are additional spend.

## Report correction

The initial health script multiplied every model by three and printed a stale three-model
label. That was wrong for the selected study. Corrected only the reporting calculation:
apply the model-specific repeat schedule, exclude historical Llama, and expose missing-model
coverage. The all-three-repeat value remains explicitly hypothetical. A regression test now
covers single Sol/control billing and incomplete model coverage. No calls, keys or prompts
were changed. This correction does not require a rerun.

## Temperature control limit

The host accepted temperature zero. With one answer per item, this pilot cannot estimate
within-item variation or establish that the host honoured temperature internally. Preserve
the control; do not interpret different items or output formatting as a determinism test.

## Next work

With health reviewed, compute saved-answer accuracy offline. Then write the remaining 81
items and four policies, add independent policy calculators and build assertions, and perform
the blind audit before freezing. Preserve all 21 development samples and their raw responses.
Report newly written held-out items separately if the full 102 includes those samples.
No further paid calls are needed until the full-set preflight/evaluation is ready.
