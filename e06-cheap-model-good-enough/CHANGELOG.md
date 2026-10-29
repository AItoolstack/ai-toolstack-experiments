# E06 change log

Maintain this record alongside `PROTOCOL.md` and the canonical draft linked from `PUBLICATION.md`.
Do not rewrite the original pilot to match a later interpretation.

## 25 October 2026 — original pilot

- Read the original design before running models. Initial Llama invocation found no OpenRouter
  key; no answer rows were saved. A subsequent attempt exhausted five retries on four workers.
  The original runner suppressed underlying retry details, so the exact cause remains unknown.
- Later diagnostic calls succeeded, including four concurrent calls and native tool output.
  This established recovery, not a proven cause of the earlier failure. Diagnostic answers
  were not added to scored results.
- Original saved coverage: Llama 21, OSS-20B 21, Sol 7 invoice answers. Sol stopped with HTTP 400:

```text
Function tools with reasoning_effort are not supported for gpt-6.1-sol in /v1/chat/completions.
To use function tools, use /v1/responses or set reasoning_effort to 'none'.
```

- Original pilot raw files remain under `results_samples/`. Llama `tl03`, repeat 0, line 11,
  returned several native tool calls. No saved original row had a length finish reason,
  unreadable answer or detected JSON tool call returned as text.
- Analysis was originally stopped after the API failure. It was subsequently run during the
  authorized infrastructure revision, with incomplete coverage explicitly reported.

## 25 October 2026 — runner v2 and analysis v2

### Request and storage changes

- Use OpenAI Responses for every OpenAI task, retaining low reasoning effort. Normalize
  Responses output text, function calls, incomplete status and token usage into the saved row
  shape. Keep OpenRouter Chat Completions and Groq routing unchanged.
- Set `strict: false` on Responses function definitions. Preserve the original tools, optional
  arguments, prompts, token budget and possibility of multiple calls. No native tools execute.
- Preserve full returned text instead of silently slicing it to 3,000 characters.
- Record sanitized retry diagnostics and include retry/backoff time in revised answer latency.
  Fatal/exhausted errors return exit code 1. No credentials or authorization headers are logged.
- Add `--run-tag` and configuration fingerprints to prevent incompatible or legacy appends.
  Add separate `--preflight` results: one example per task, excluded from scored pilot data.
  Dry-run replies are deterministic by item/repeat even with multiple workers.

### Measurement changes

- Preserve baseline checks and report revised checks alongside them on the same answers.
  V2 adds calendar validity, invoice value types, tool schema types, incomplete/empty answers
  and chronological meeting bounds. Neither validator reads the answer key.
- Grader fixes: missing invoice keys no longer equal explicit null; malformed/non-object
  arguments fail safely; invalid tool schema/types fail; unreadable amounts and cutoffs are
  recorded separately. The item documents, keys and numeric tolerance are unchanged.
- Report all four validator outcomes, accepted-answer accuracy, error catch rate and
  escalation rate. Undefined rates are null. Report unique item counts and trap denominators.
- Require complete task/overall paired coverage for check cascades; require exactly the first
  three cheap repeats for agreement. One repeat now reports agreement as unavailable.
- Keep costs and latency qualifications explicit. Failed-attempt charges are unknown; simulated
  sequential cascade latency is labelled as an estimate. Source and raw-result hashes accompany summaries.
- Write summaries to dataset/tag-specific analysis folders with a row audit and stable item IDs.
- Set repository Ruff target to Python 3.10, matching the documented minimum and installed
  runner. No E01 source files were changed.

### Revised pilot and artifacts

- Preflights passed for Llama, OSS-20B and Sol: nine separate compatibility calls.
- Revised pilot saved all 63 answers (21 per model, one repeat) under `results_samples_v2/`.
  Scores: Llama 9/21, OSS-20B 20/21, Sol 21/21. Every answer passed both validators; all 13 wrong
  answers escaped. The check cascade therefore never escalates. Agreement remains unavailable.
- No revised saved row is cut off, unreadable, or detected as a text-form tool call.
- Original pilot results are not pooled with the revised pilot. Score differences do not
  establish an effect of the adapter or any other intervention.
- Added README, revised protocol, regression suite, chart script and saved-results notebook.
  Publication draft and evidence map live in the canonical site workspace, linked from `PUBLICATION.md`.
  The draft follows E01's example-led first-person tone and labels these results as a pilot.
- Existing user deletion of `.env.example` was left alone. `.env` remains ignored; no secrets
  were printed or committed. No commit, push, live publication or public message was performed.

### Validation

- Offline regression suite covers API request/response contracts, preserved full text,
  retry redaction, HTTP 400 handling, failed-run exit codes, malformed argument shapes/types,
  missing fields, invalid dates, nonfinite amounts, cutoff flags, incomplete cohorts and
  consistent-but-wrong repeated answers.
- Python 3.10 compilation and Ruff checks are run on changed experiment Python files.
- Original and revised saved-results analysis, baseline comparison and chart generation are
  reproduced locally. A three-repeat scripted dry run checks complete cascade reporting.
- Notebook code cells are executed against saved data; chart PNGs are visually checked.
- Matplotlib 3.10.9 generated the three PNG/SVG chart pairs. Verified copies are included inline
  in the local article draft. Chart/lint dependencies were installed into a temporary target
  folder, without changing the experiment's standard-library runtime requirements.
- Protected item/tool/generator files are compared with Git; no changes are permitted.
- A credential-value scan of experiment and publication artifacts passed without printing keys.
- Markdown source and links are reopened and checked. The site content folder has no applicable
  article build command; no theme files are changed.

## Remaining work before a full study

- Independently audit the answer key; freeze a separate unseen set, prompts, validators and
  prices before evaluation. The full 102-item set and extra policies do not yet exist.
- Run the planned models with three repeats on that set, then add paired uncertainty estimates
  by resampling whole items. Do not treat repeats as independent item counts.
- Test source-supported arguments and rule calculations as separate workflow variants if desired.
  These have not been implemented or measured here.
- Update the maintained draft, figures, repository links and evidence map after every material
  run or interpretation change. Retain the pilot caveats until the full study is complete.

## 29 October 2026 — handover reconciliation and six-model preparation

- Tej selected the six-model handover lineup and asked to continue aiming for the earlier
  deadline. The local state is newer than the pasted handover; preserve all existing work.
- Added GLM default/control configurations, verified public endpoint metadata and prices,
  model-default 3/1 repeats, single-Sol fallback support, and control exclusion from cascades.
  Kept historical model request bodies and all sample data unchanged. Reasons and sources
  are recorded in `RESUME-2026-10-29.md`; analysis version is v3.
- Added a reproducible offline pilot-health report and an owner-run PowerShell preflight/pilot
  script with a fresh tag and stop-on-error behaviour. No paid inference calls were made.
- Reproduced saved results and validated all six configurations offline. The new blind audit,
  evaluation set, freeze and live six-model compatibility checks remain outstanding.

### Owner-run six-model preflight inspected

- Tej completed all 18 compatibility calls under the new preflight tag. Inspected every
  response: correct hosts, current fingerprints, native tool calls, present token accounting,
  no cutoffs or retries. GLM's default invoice wraps JSON in a fence, accepted by the existing
  parser; preserve this format caveat without changing prompts.
- Saved the source hashes and compatibility checks in the preflight analysis folder, with
  a human-readable `PREFLIGHT-REVIEW-2026-10-29.md`. Successful-call list-price cost is
  $0.006318175. The pilot-only coarse estimate is $0.04423, pending harder-item measurements.
- The preflight gate is passed. The six-model pilot, full dataset, independent audit and
  freeze remain outstanding. The assistant made no paid calls or credential reads.

### Owner-run six-model pilot inspected

- Tej completed all 126 pilot calls. Reviewed coverage, routing, fingerprints, token usage,
  completion states, and 54 selected answers before computing accuracy. No cutoff, unreadable
  answer, or retry was recorded. Fenced JSON remains accepted under the existing parser.
- Manual review found OSS-20B `tl03` claiming ticket creation in prose without a native call.
  Preserve the failure; model-versus-host attribution is unresolved from saved telemetry.
- Fixed the pilot-health projection's stale all-three-repeat assumption and misleading label.
  The actual six-model 1,428-call projection is $0.33168, or $0.46784 with double output.
  Added a regression test; no experimental request, prompt or gold answer changed.
- `PILOT-REVIEW-2026-10-29.md` records the seven checks, caveats, costs and next steps.

### Full set and independent audit

- Added 81 items and four fictional policies, with Decimal calculators for all five policies.
  Added count, trap, invoice arithmetic/sign, date and rule-key assertions. Explicit LF
  writing preserves exact sample/tool bytes and historical request fingerprints on Windows.
- A fresh key-blind agent answered 102 items before seeing labels. One answer disagreed.
  Label review and four source re-audits resolved 17 items, including six changed keys.
  All original answers, interpretations and old/new decisions remain preserved.
- Final difficulty mix: 34 clear, 60 hard, 8 contested. Every trap retains at least three
  examples. See `AUDIT-2026-10-29.md` and `audit-resolution.json` for each reason.
- Analysis v4 reports trap/kind counts and separates held-out/development cohorts, checking
  the dataset hash and writing separate outputs. Scripted runs are not model evidence.
- Added freeze verification and owner-run preflight/evaluation scripts. Scoped Git
  attributes preserve exact E06 bytes so audit/data hashes survive platform checkouts.

- Final validation passed: 21 regressions, compilation, Ruff, 1,428 scripted answers and
  complete all/held-out/development cascade reports. Original sample/tool bytes and blind
  first-pass answers match their recorded hashes. No new paid calls or publication occurred.

### Completed frozen evaluation and offline results

- Tej completed 1,428 calls. Freeze/configuration/routing/coverage checks pass. GLM `rl10`
  repeat 0 exhausted 2,000 tokens; the control's `tl03` returned two calls. Tej approved
  retaining the cutoff as a frozen-budget failure before accuracy inspection. No paid rerun,
  cap increase, key, item, request or original frozen-scorer change.
- Successful-response list-price cost is $0.311058475, excluding earlier/preflight calls.
  No retries or separate API error logs were recorded.
- Held-out checks catch 2/58 wrong cheap responses and accept 56. Agreement scores 77–80/81
  at $0.40–$0.62 per 1,000 items; Sol scores 79/81 at $1.51. Do not infer equal reliability.
- Added the deferred paired whole-item bootstrap, 10,000 draws, seed 6, fixed task mix;
  its point estimates independently match the frozen scorer. Synthetic tests cover repeat
  clustering, stratification/pairing, consistently wrong answers and cascade cost.
- Exported all wrong/accepted answers and count-only kind/trap reports. Added full-result
  reproduction and a visually checked 2x PNG/SVG chart with Inter, licence and actual-number
  alt text. All original frozen hashes still verify.
- Article rewriting awaits the required claude/style-guide.md. No public account write,
  publication, message, Git push or additional inference call was made by the assistant.
