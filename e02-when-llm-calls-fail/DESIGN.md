# E02: what happens when an LLM call fails?

Status: **design and development pilot for Tej's review; 1 November 2026**.
Written before running the E02 pilot. No full evaluation is authorized by this document.
The initial implementation request authorizes building a reviewable design and pilot.
The supplied brief requires Tej's review after those artifacts, before the full run.

## Question and contribution

On the same synthetic workflows, how do defaulting, retrying, falling back and explicitly
reporting failure change wrong completed results, correct results, unavailable results,
calls, estimated cost and modelled waiting time? Report outcomes per 1,000 tasks alongside
raw counts and distinct-item denominators. This measures consequences under specified
failures; it does not measure how often providers fail in production.

E01 taught us that easy examples hide problems and LLM judges introduce disagreement.
E06 supplied audited, deliberately tricky examples and deterministic scoring, but showed
that plausible incorrect answers pass structural checks. E02 therefore separates failure
detection from correctness, never gives the answer key to the recovery policy, and retains
incorrect completed responses. A fallback can be wrong. Saying so cannot detect every error.

## Data, cohorts and response reuse

Use E06's unchanged `items.jsonl`, `dataset-manifest.json`, tools, policies, scorer,
audit record and all six files in `results_frozen_20261029/`. Validate 102 distinct items,
1,428 unique expected model/item/repeat records, recorded tokens/timing, and cohort partition.
Record the original cutoff and multiple-tool-call record in input health, without replacing
them. Hash inputs and imported scorer dependencies. Never modify E06.

The primary pair is **oss-20b -> sol** (Groq -> OpenAI as recorded by E06). These are
historical identifiers and frozen historical list prices, not current product claims.
Use primary repeats 0, 1, 2 as separate paired replay tracks. Sol has only repeat 0.
Every retry on a track reuses that same saved response: we model transport recovery, not
fresh response sampling or prompt repair. Fallback always reuses Sol repeat 0.

Headline cohort: E06's 81 held-out items (29 invoice / 29 tool / 23 rules).
Report E06's 21 development items separately. These are reused E06 held-out items, not a
new unseen E02 dataset. Auditing corrected labels; it did not remove template dependence.
Do not author new tasks for this study. Tool calls are selected actions; none executes.

Pilot selection is fixed now: `inv01`-`inv04`, `tl01`-`tl03`, `rl01`-`rl03` (10 development
items). Pilot uses seed 20261101 and primary repeat 0. Full run uses seeds
20261101 through 20261110 and all three primary tracks. Seeds/repeats are not new items.

## Observable failure detection, shared by all designs

Reject an injected 429 or timeout; `finish_reason=length`; other incomplete/filter finish
states; absent visible content AND absent native calls; unreadable JSON; missing invoice
keys or invalid basic field types; rules without a finite numeric amount; invalid tool
argument JSON/schema; more than one native tool call. A valid native tool call with empty
text is a valid response. Nonempty tool prose without a native call remains accepted, as
in E06: its truth cannot be established by these checks. No arithmetic, source comparison,
answer-key lookup, or semantic judge is used for detection. JSON extraction deliberately
reuses E06's lenient fenced/embedded-object parser; this is not strict JSON compliance.

Native source faults remain observable whenever an attempt is not intercepted. Retrying
cannot fix a native fault because its saved response is unchanged. Preserve both injected
and native classifications per attempt. E06's real GLM cutoff is an input-health observation,
outside the selected primary pair, not an injected recovery measurement.

## The four policies

Every failure kind gets the same fixed limits. A syntactic failure is not silently repaired.
`N=2` retries means three primary attempts in total. Backoff is deterministic: 1 second
before attempt 2 and 2 seconds before attempt 3. No real sleeping occurs.

| Design | Attempt sequence | Exhaustion behaviour |
| --- | --- | --- |
| default | primary once | emit task default as completed |
| retry | primary up to three times | emit task default as completed |
| fallback | primary up to twice, then fallback once | emit explicit couldn't-check if fallback fails |
| say_so | primary up to twice | emit explicit couldn't-check |

Fallback is immediate after the second primary failure, with no extra backoff. It has no
retry. Every successful-looking response is accepted even if the scorer later finds it wrong.
No deadline, circuit breaker, jitter, prompt change, idempotent business operation, or live
queue is tested. All four share the detector so we isolate recovery behaviour.

### Defaults by task: assumptions, not observed E06 behaviours

E06 does not implement silent defaults. These choices are explicit synthetic pipeline
behaviours, motivated by its nullable extraction schema and numeric/no-call output shapes.
They are not evidence of what most pipelines do, and must be approved during design review.

| Task | Completed default | Interpretation |
| --- | --- | --- |
| Invoice | null strings/dates/currency; numeric totals 0; is_credit_note false | lost extraction appears as an empty, zero-value record |
| Rules | amount 0, rules_used empty | a failed check appears to award nothing |
| Tool | no native call; text `No action selected.` | a failed selection appears completed |

Score invoice/rules defaults with E06's exact scorer. A tool default is wrong when a tool
was required. When the key requires no call, classify it as **unverified**, not correct:
E06's key cannot establish that this default gave the necessary clarification/refusal.
Report four mutually exclusive outcomes: correct, wrong, unverified, couldn't-check.
Headline wrong counts exclude unverified; also give [wrong, wrong + unverified] bounds for
possibly misleading completed results. Do not equate inaction with a completed workflow.
Accepted nondefault no-call prose retains E06's coarse action grade; this remains a limit.

An invoice default with null numeric fields is a predeclared sensitivity, evaluated separately from the
primary zero-numeric default on the identical schedules. Do not pool the two. It tests
whether the chosen numeric default drives the result; it is not a fifth recovery design.

## Failure model, fixed before pilot

One 0% no-injection control, then a Cartesian product of:

- rates 0.01, 0.05, 0.20;
- failure kinds `rate_limit`, `timeout`, `cutoff`, `malformed_json`, `empty`;
- regimes `independent`, `persistent_primary`, `persistent_shared`.

Thus 46 scenarios, with no invented production mixture weights. Interpret rate as per-call
probability in independent scenarios and per-task episode probability in persistent ones.
Report realized initial and all-attempt rates; the all-attempt rate is policy-dependent.

Use a SHA-256-derived uniform variate keyed by seed, item ID, replay track, model role and
attempt index; compare with the rate. Common keys give paired schedules across policies,
both default variants and rates. Independent fallback uses its own role key. Scenario kind
and rate do not enter the key, so initial triggers nest as rates increase and are paired
across failure types. Adding/reordering items or resuming must not change schedules.

In persistent_primary, a single item/track trigger makes every primary attempt fail;
fallback has an independent probability p of failing. In persistent_shared the same trigger
makes primary AND fallback fail. These are stylized failures lasting an entire task, not
calendar-time outages or measured host correlation. Cross-host sharing is a stress case,
not a claim that these particular hosts share infrastructure. The 0% control has no
injected failures; native faults, if present, are retained.

Inject realistic observable failure shapes: transport status without content; timeout;
saved body with length finish; deliberately broken invoice/rules JSON or tool arguments;
empty content and calls. Cutoff is detectable even if the remaining JSON happens to parse.

No queue/capacity model is present. Report retry amplification and lack of recovery under
persistence, but **do not claim to measure a 429 storm, queue growth or congestion caused
by retries**. Those require a separate capacity experiment.

## Calls, historical cost proxies and modelled time

Each attempted request counts, including rejected ones. Successful and native-fault attempts
use their saved latency and historical input/output token prices, never double counting
reasoning tokens. Reused response rows are proxies for hypothetical attempts, not live calls.

| Injected failure | Modelled attempt seconds | Lower/upper USD proxy |
| --- | --- | --- |
| 429 | 0.2 | 0 / saved successful-call cost |
| timeout | 30 | 0 / saved successful-call cost |
| cutoff | saved call seconds | input + 2,000 output tokens, same at both bounds |
| malformed JSON / empty | saved call seconds | saved successful-call cost, same at both bounds |

These are scenario assumptions, not provider billing guarantees or measured failure timing.
Cutoff latency is a weak proxy, not a token-speed model. Timeout upper cost is only the
saved-call proxy, not a universal bound on billed spend. Also show successful-response-only
cost. API spend for running this code is exactly $0: no network client, keys or .env needed.
There is no live check in this milestone.

Sum sequential attempt proxies plus backoff. Report mean and p95 total modelled seconds,
and differences from each design's same-item/seed/track 0% control. Percentiles of modelled
times are not production service percentiles.

## Scoring, uncertainty and accounting

Policies emit content references/defaults or an explicit unavailable status. Only analysis
reads gold labels. Export every attempt, injected type, native fault, terminal result,
source file/line reference, and accounting value. No attempt can disappear from the ledger.
Wrong results are partitioned into baseline-correct -> wrong (introduced) and
baseline-wrong -> wrong (inherited/persisting); baseline is the raw first primary response.
Also count baseline-wrong -> correct (recovered). These are paired descriptive transitions,
not causal attribution when retries/fallback alter which response is selected.

For each scenario, default variant, design and task/all: counts and denominators, distinct
items, rates per 1,000, calls, extra calls over one, failures per type, failure-detection
reasons, estimated cost bounds and modelled time. Include paired differences against
default and against the 0% control. Never pool failure types into a production-rate claim.

Average all seeds/tracks within an item, then task-stratified paired item bootstrap:
10,000 draws, seed 20261102, percentile 95% intervals. Use the same selected items for
all four policies and control comparisons. Report intervals for outcome rates, mean calls,
cost and mean latency. p95 remains descriptive. Separately report min/max across the ten
seed-level means (Monte Carlo spread, not an item confidence interval). Template/policy
dependence and the single reused Sol answer remain outside these intervals. Compare
paired-difference intervals; overlapping marginal intervals are not a significance test.
The 10-item pilot uses 200 draws for diagnostic checks only; these are not final intervals.

Worked-example rule: first held-out baseline-correct -> wrong default result at independent
5% timeout, ordered by item ID, seed, track; if none, explicitly report none. Show that same
task/schedule across all four designs. Export all candidate examples so the choice is auditable.
The pilot instead shows its first emitted default ordered by scenario ID, item, seed and
track, labelled as a development trace rather than the publication example.

## Expectations, surprises and ways this can be wrong

Independent retries should reduce injected failures, by construction. Persistent failures
should expose their limit. These arithmetic consequences alone are not discoveries about
providers. The empirical contribution is how these policies interact with real saved
wrong answers, task defaults and fallback responses on these particular synthetic tasks.

Surprises would include fallback increasing wrong completed results, defaults often
matching keys, or extra attempts buying little correct coverage even under independent
failures. Say-so looks unattractive if it substantially reduces correct coverage while
preventing few wrong completions, or if users cannot tolerate its unanswered share.
Do not select an acceptable unanswered threshold after seeing results: report the frontier;
the acceptable tradeoff depends on the workflow and remains a reader decision.

What could invalidate a claim: label mistakes, unaudited source changes, unequal schedules,
response/seed repeats treated as independent items, conflating no call with useful help,
unjustified defaults, cost proxies presented as bills, retries treated as new samples,
unmodelled side effects, a fallback that shares an outage, or synthetic tasks presented as
production prevalence. Simulation intervals do not validate the failure assumptions.

## Freeze and review gate

The initial FREEZE.json is a **review snapshot**, not an approved evaluation freeze.
It pins design, configuration, code, tests, fixtures and E06 inputs before the pilot.
`freeze.py --check` verifies it. The full runner requires a separate APPROVAL.json binding
Tej's recorded approval to that exact review snapshot; no approval exists initially.
After review, log changes below, regenerate the review snapshot explicitly if needed,
rerun the pilot/checks, then record actual approval before the evaluation. Never silently
overwrite either snapshot. Exploratory changes/results belong in separate files.

Deliver now: design, offline harness, build checks, analysis/uncertainty implementation,
unit tests, pilot data/report and reproducible commands. Full-results, claim map, figures
and post handover are generated only after approved evaluation; no blog post is written.

## Changes after review

None. No full-run review or approval has happened yet.
