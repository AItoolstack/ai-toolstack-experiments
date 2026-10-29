# Frozen evaluation health: 29 October 2026

All 1,428 expected answers are saved under `results_frozen_20261029/`. The original freeze
still verifies at `e06-frozen` (`ffaf7e3`); no frozen item, key, prompt, model, route, price,
repeat setting or analysis source was changed. No accuracy summary was read or generated
before this health review. The handover's no-cutoff gate is not cleanly passed.

## Seven checks

1. **EXCEPTION — unreadable answers:** one GLM Flash response, `rl10` repeat 0, has no
   visible answer. Its token-cap cause is documented below. There is no evidence of a shared
   prompt/format fault; all other invoice/rules responses parse through the frozen parser.
   Fenced JSON remains accepted and is not strict JSON-only compliance.
2. **FAIL — no cutoffs:** the same response reports `finish_reason=length`, 2,000 completion
   tokens and 1,999 reasoning tokens. The cap was reached, not ignored. Source:
   `results_frozen_20261029/glm-flash.jsonl`, line 119. Retain this record without replacement.
3. **EXCEPTION — tool diagnostics:** GLM-t0 `tl03`, repeat 0, returns two native calls,
   `get_order` followed by `create_ticket`; the instruction permits at most one. Source:
   `results_frozen_20261029/glm-flash-t0.jsonl`, line 38. Both argument objects are readable;
   this is a multiple-call failure, not malformed JSON. No structured JSON tool-call-as-text
   flag was detected. Manual review of every no-native-call reply also found prose action
   claims, including OSS-20B `tl21` repeat 1 and `tl34` repeat 2 saying a ticket was created
   without a native call. Retain these workflow observations. Saved normalized rows do not
   provide host-parser telemetry sufficient to attribute all such failures to model weights.
4. **PASS — routing and frozen identity:** every OSS row reports Groq, every GLM row Z.AI,
   and every Luna/Sol row OpenAI. Request fingerprints match. Coverage is exactly 306 rows
   per cheap candidate and 102 each for Sol/control, with all required item/repeat pairs.
5. **PASS — usage and transport accounting:** input/output/reasoning counts are present.
   Zero reasoning is a reported value. No reported output exceeds 2,000 tokens. Every saved
   response reports one attempt, and no separate error logs or retry records were found.
   Completion counts include reasoning; do not charge it again.
6. **PASS WITH FINDINGS — manual prompt review:** inspected `inv01`–`inv03`, `tl01`–`tl03`,
   and `rl01`–`rl03` at repeat zero for every model: 54 answers, plus all exceptional rows
   and every tool reply without native calls. No shared prompt defect warrants changing the
   frozen experiment. The cutoff and multiple-call exceptions remain visible.
7. **PASS — cost:** all 1,428 saved answers total **$0.311058475** at frozen list prices.
   This is successful-response token accounting, not billing reconciliation. Preflights and
   development calls are additional spend. No retries were observed in this evaluation.

The machine-readable diagnostics, result hashes and costs are in
`analysis_frozen_20261029/run-health-2026-10-29.json`.

## Methodological decision

The handover requires “No cut_off” before accuracy analysis. Tej explicitly chose on
29 October 2026: “Count it as a frozen-budget failure and continue analysis”. This permits
descriptive accuracy analysis with a disclosed health exception. Retain the original row;
do not increase the cap, drop the item, replace its answer or make another paid call.

The multiple-call control response is already a failure under the frozen one-call instruction.
No source changes or extra model calls are needed to preserve either observation.
