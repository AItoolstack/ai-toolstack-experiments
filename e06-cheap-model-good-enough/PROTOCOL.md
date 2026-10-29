# E06 protocol amendment: 25 October 2026

This amendment follows the first pilot. It is not a claim that the revised checks were specified
before seeing model answers. The original design remains in `DESIGN.md`; changes are tracked in
`CHANGELOG.md`.

## Question and scope

Can simple checks make a cheap model reliable enough for a particular workflow, and which
incorrect answers still pass? Report by task before reporting an equally weighted combined score.
The item mix is deliberately difficult and does not estimate the frequency of errors in a customer workflow.

The 21 sample items are development data. Preserve their documents, prompts, answer key and
original raw results. A new run is a new observation, not a replacement for an inconvenient result.
The original pilot and revised pilot differ in API handling and sampling time; their score difference
is not a causal estimate of an improvement.

## Baselines and revisions

All models receive the existing task instructions and tools. Llama has no reasoning setting;
the other configured models use low reasoning effort. OpenRouter remains pinned to Groq with
fallbacks disabled. OpenAI uses Responses for every task. Tools explicitly use `strict: false`
so the adapter does not silently add constrained decoding. Multiple calls remain possible and
are graded as failures under the existing one-call instruction.

Official API references checked during implementation:

- [Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)
- [Function calling and strict mode](https://developers.openai.com/api/docs/guides/function-calling)

Two validators are reported against the same saved answers:

- **baseline:** the original arithmetic, date-order, credit sign, required-tool-argument, enum,
  past-time and nonnegative numeric answer checks. Parser crashes and nonfinite numbers are
  handled safely, so this is compatible with ordinary pilot rows rather than a byte-for-byte old scorer.
- **v2:** also rejects incomplete responses, invalid calendar dates even without a due date,
  incorrect invoice value types, invalid tool argument types, empty no-call replies and reversed
  meeting times. This is a development revision made after seeing pilot data.

Neither validator reads the gold answer. Neither establishes that a date or amount was supported
by the source, that the chosen tool was the correct first step, or that a refund ID was supplied
by the user. Those semantic checks are outside this version. Do not describe schema checking as
source validation. Future evidence checks should be a separate, frozen experimental arm.

Grading uses the existing key, with robustness fixes: missing invoice keys cannot stand in for
explicit nulls; invalid tool schema/types fail; non-object tool arguments cannot crash the scorer;
unreadable amounts and incomplete output have separate flags. Numeric tolerance remains below
0.5p as implemented in the original scorer. The key and tolerance have not been fitted to results.

## Denominators

Report saved calls and distinct items, with expected coverage. A partial model's accuracy is
labelled observed-only. Per-trap figures include item and call counts; traps can overlap.
Three repeats of one item are correlated observations, not three independent test cases.

For the check cascade, use every expected item/repeat in the selected task for both models.
For agreement, require repeats 0, 1 and 2 for every cheap-model item, using repeat 0 of the
fallback when escalation is required. Retain the cheap model's repeat 0 when all three match.
Overall estimates require all tasks. Task-specific complete estimates are labelled by task.
No estimate is produced for incomplete cohorts.

Each validator reports the four outcomes separately: correct accepted, correct escalated,
wrong caught and wrong accepted. Undefined rates are null, not zero. Free-text tool arguments
are only checked for presence where the original key says so. Tool no-call grading does not
judge the wording of a clarification. Agreement compares normalized selected actions and
arguments; identical mistakes can pass it. No majority-vote or semantic-equivalence claim is made.

## Costs, latency and failures

Costs use the configured list prices and reported input/output tokens from saved answers.
Reasoning tokens are already included in output tokens and are not added twice. These are
estimates, not billing reconciliation; caching discounts and failed-attempt charges are unknown.
Preflight and development calls are additional experiment spend, outside the policy simulation.

Revised latency spans all attempts and backoff for a saved answer. Original pilot latency only
spans its final attempt. Cascade latency sums sequential calls from the saved runs; it is not
an observed concurrent service latency. Compare cost and accuracy on the same complete cohort.

Fatal or exhausted calls stop with exit code 1. Sanitized attempt diagnostics are kept separately
from answers. In-flight workers may still finish and save their answers after another worker
fails. Keep those records; do not silently rerun or change model settings to hide an API failure.

## Before the full evaluation

1. Finish development on these samples. Do not call them unseen results.
2. Prepare the planned evaluation set in a separate, explicitly authorized item-building pass.
   The 102-item set and additional policy documents are plans, not completed artifacts.
3. Audit expected answers independently of model outputs. Log disagreements and accepted
   alternatives. The blind audit has not been completed in this revision.
4. Freeze items, key, prompts, checks, model IDs, endpoints, host routes, prices and analysis
   version with hashes before the first evaluation call. Preflight all included task types.
5. Run the planned models three times on the frozen set. Keep transport failures visible.
6. Report paired differences with uncertainty by resampling whole items, keeping each item's
   repeats together. This uncertainty analysis is deferred until an unseen evaluation exists.
7. Choose worked examples by a stated rule (for example, every wrong answer that passed checks),
   not only the most dramatic case. Report disagreements with the key before drawing conclusions.

No claim of statistical superiority, deployment readiness, or savings at equal reliability is
supported by the current pilot. The draft article must retain that qualification until the
unseen-set evaluation, independent audit and uncertainty analysis are complete.

## 29 October 2026 — six-model resumption amendment

Tej selected all six models in the handover. `RESUME-2026-10-29.md` records the changes and
their reasons. This supersedes the earlier all-model three-repeat plan: the four cheap
candidates get three repeats, while Sol and the temperature-zero control get one. Both
cascades reuse Sol's repeat zero; the control is excluded from cascades. Its one answer per
item cannot establish within-item temperature stability. Preserve the older Llama pilot as
development history. Report any retained development items separately from newly written
held-out items. The independent audit and freeze gates continue to apply.

## 29 October 2026 — completed item audit

The full 102-item set exists, including 21 development examples and 81 new items.
Independent blind answering, label review and four source re-audits are complete.
`AUDIT-2026-10-29.md` records 17 changed items and the final 34/60/8 difficulty mix.
Four calendar-owner cases accept both attendee conventions and are contested. Ambiguous
required dates instead require clarification. No system prompt was tuned per model.
Use separate held-out/development summaries. Original sample keys and pilot rows are preserved.
