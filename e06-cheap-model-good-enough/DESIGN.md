# E06 design: is the cheap model good enough?

Status: **design approved 26 Oct 2026 (changes logged at the end). Nothing has been run against a real model yet; the pilot is next.**
Written before any run so the answer key, the failure types and the comparisons can't be fitted to the results afterwards.

## The question
Where does a cheap model fail on ordinary production tasks, and can a cheap check catch those failures before they cost anything?

"Good enough" has no meaning without a task and a fallback. So the experiment measures accuracy per task and per failure type, and it also tests two ways of using a cheap model safely: keep its answer unless a code check fails, or keep it unless three runs of it disagree, and otherwise hand the case to a larger model.

## Three tasks, graded by code
No LLM judge. E01 showed judges disagree with each other by up to 27 points on the same answers, so every answer here is compared with a written key.

| Task | What the model gets | What it must return | How it's graded | Planned items |
|---|---|---|---|---|
| Invoice extraction | One messy invoice or credit note (UK, German, French, US layouts; OCR noise) | 10 fields as JSON | Each field exact after normalising (amounts to 1p, ISO dates, company suffixes) | 36 |
| Tool calling | An operations assistant's system prompt, 9 tools, one request | One native tool call, or no call (ask / decline) | Tool name exact; arguments by type (datetimes as instants, lists as sets, free text only for presence) | 36 |
| Rules over a document | A one-page policy (rail delay compensation in the sample; four more policies to come) and a case | An amount in pounds | Within 0.5p | 30 |

An item counts as correct only if every graded part is right. Field-level and argument-level errors are kept for the analysis.

Why these three: they're the jobs teams most often hand to a cheap model, and each has an answer that can be checked without opinion. Two candidates were dropped. Long-label ticket routing needs a label set someone else would agree with, and code-review triage can't be graded without a judge.

## Traps, written down before the run
Every hard item is built to test one or more named failure types. The analysis reports accuracy per trap, so the error taxonomy is fixed now, not invented from the results.

- **Invoice:** number_format (1.234,50 / 1 595,00), date_format (DD/MM vs MM/DD, decided by context), computed_due_date (Net 30 from the invoice date), amount_due_differs (deposits, part payments), credit_note (negative amounts), decoy_reference (an invoice or PO number that isn't the document's own), party_confusion (bill-to block printed first), ocr_noise (0/O, l/I), missing_field (null, not a guess), foreign_language.
- **Tool:** first-step items have one right first call, and asking the user for something a tool could look up is counted as its own error, `asked_instead` (tl05: look up Tom Okoye, don't ask for his email; decided 26 Oct). relative_date ("this Friday"), default_attendee, policy_override (a refund over £100 must become a Finance ticket), missing_argument (must ask), first_step_only (look someone up before emailing them), format_conversion (€45 to amount + ISO codes), enum_mapping ("sent back" to status "returned"), similar_tools (get_order vs search_orders).
- **Rules:** derived_base (half a return fare, a season ticket's daily fare), rounding, threshold_minimum (under £1 pays nothing), order_of_operations (round, then add 10% for vouchers), exception_tier (the 120-minute tier uses the return fare), exclusion (a refunded ticket can't also claim), distractor_numbers.

## Mix
Three kinds, assigned by a fixed rule that `build_items.py` checks when it writes the file:
- **clear**: no trap. Any competent model should get it; a miss here is a real problem.
- **hard**: built to test at least one named trap.
- **contested**: two readings are defensible and the key accepts both (for example `due_date` null or the invoice date for "payment due on receipt").

Target: about a third clear, the rest hard, a few contested. E01's first item set was too easy and every model scored 100%, so the hard share is deliberate. The 21 samples are 3 clear, 16 hard, 2 contested, so most of the remaining items must be clear to reach the target.

Results are reported per kind as counts.

## Models: a price ladder, one prompt for all
| Short name | Model | Host | $/M in | $/M out | Reasoning | Runs per item |
|---|---|---|---|---|---|---|
| oss-20b | gpt-oss-20b | Groq via OpenRouter | 0.075 | 0.30 | low | 3 |
| luna | GPT-6 Luna | OpenAI | 0.10 | 0.50 | low | 3 |
| glm-flash | GLM-5.3-Flash (open weights, MIT) | Z.ai via OpenRouter | 0.15 | 0.50 | low | 3 |
| oss-120b | gpt-oss-120b | Groq via OpenRouter | 0.15 | 0.60 | low | 3 |
| sol | GPT-6.1 Sol | OpenAI | 2.00 | 10.00 | low | 1 |
| glm-flash-t0 | GLM-5.3-Flash at temperature 0 (control) | Z.ai via OpenRouter | 0.15 | 0.50 | low | 1 |

Prices checked 25 Oct 2026 (Groq, OpenAI) and 26 Oct 2026 (GLM-5.3-Flash) on OpenRouter's endpoint lists and OpenAI's price page. Both gpt-oss sizes run on the same host, so that pair is the cleanest size comparison. GLM-5.3-Flash is pinned to Z.ai, its maker: cheaper hosts list it from $0.05/M in but don't state how they quantise it.

**Temperature.** run.py sends no temperature, so each host's default applies (Groq: 1.0). That is how most teams call these models, and the agreement cascade needs run-to-run variation. To show how much of that variation comes from sampling, `glm-flash-t0` repeats the GLM run once at temperature 0. It's a side measurement and is left out of the cascades. If the pilot shows the host ignores temperature for this reasoning model, the control is dropped and the write-up says why.

**Sol runs once per item.** It is the top rung and the fallback in both cascades. The write-up reports accuracy per item, and E01 already covered run-to-run consistency, so two more Sol runs per item would add cost, not evidence. The limit this creates: Sol's own variation isn't measured.

## Cascades (no extra calls)
Both are computed from the runs above. When the cheap answer is escalated, the fallback's single answer on that item is used.
1. **Check:** keep the cheap answer unless a code check fails. The checks use no answer key: JSON parses, net + tax = gross, dates valid and due ≥ issued, credit-note sign; the tool exists, required arguments present, enum values valid, times not in the past. For the rules task the only check is "a number came back", so I expect this cascade to do almost nothing there. That's a finding, not a flaw.
2. **Agreement:** run the cheap model three times and escalate when the three answers differ.

Reported: accuracy, share escalated, and cost per 1,000 items, against the large model alone. The agreement cascade is charged all three cheap calls.

## Cost estimate (full set: 102 items; 3 runs for four models, 1 for Sol and the control = 1,428 calls)
Prompt sizes measured on the sample items (invoice ~320 tokens, tool ~1,010 with the tool list, rules ~500), rounded up. Output lengths are estimates; the pilot replaces them with measured counts before the full run.

| Model | Calls | Cost | If output is 2× |
|---|---|---|---|
| oss-20b | 306 | $0.05 | $0.09 |
| luna | 306 | $0.08 | $0.14 |
| glm-flash | 306 | $0.09 | $0.15 |
| oss-120b | 306 | $0.10 | $0.18 |
| sol | 102 | $0.67 | $1.19 |
| glm-flash-t0 | 102 | $0.03 | $0.05 |
| **Full run** | **1,428** | **~$1.02** | **~$1.80** |

**Pilot first:** all 21 sample items, one run each, on all six (126 calls, ~$0.17; ~$0.29 if output is 2×). Its job is to break things before the full run: answers that don't parse, cut-off outputs, tool calls returned as text, the wrong host, temperature ignored, the token cap ignored. (The 25 Oct draft planned oss-20b and Sol only for "$0.05"; 21 Sol calls alone cost about $0.14, and the untested paths were the ones most likely to break.)

Total budget: ~$1.19 expected, ~$2.09 if outputs run 2×. Spending caps: $3 on the OpenAI project, $1 of OpenRouter credit. Groq's free tier (about 200k tokens a day) is too small for this, so the Groq runs go through OpenRouter credit.

## What would make the result wrong
- **I wrote the items and the key.** Before any run, a separate agent solves every item blind; each disagreement is either a key fix (logged) or becomes contested. Same method as E01's rescoring.
- **102 items is small.** With about 100 items per model, differences under roughly 10 points between two models are noise. Within one task (30–36 items) the margin is about ±15 points per model, so a gap between two models on one task is only called real above about 20 points. Per trap there are only 3–6 items, so trap results are reported as counts ("2 of 5"), never percentages. The write-up says so and doesn't rank close models.
- **One prompt for all models.** A cheap model can sometimes be fixed with a better prompt. Not tested here; it's a fair follow-up.
- **Host effects.** Tool calling goes through each host's parser. A call returned as text instead of a tool call is counted as a failure (a real system would miss it) and reported separately, so it isn't blamed on the model alone.
- **One cheap model is on a different host.** GLM-5.3-Flash runs on Z.ai, the gpt-oss pair on Groq. Host differences (parsers, defaults) are mixed into GLM's result; the write-up names the host.
- **"Cheap" depends on the host.** The same gpt-oss-20b is listed at $0.018/M input elsewhere, four times cheaper than Groq. Hosts may quantise differently, so this experiment keeps one host and mentions the spread as a limit.

## Files
- `build_items.py` writes `items_samples.jsonl` (21 items for review) and `tools.json`. The full set will be `items.jsonl`.
- `run.py` calls one model and saves raw answers (resumable, `--dry-run`, `--only`).
- `analyse.py` checks run health, scores, breaks results down by kind and trap (as counts), and computes both cascades.

## Changes after review (26 Oct 2026, before any run)
1. Pilot on all models, one run each (126 calls, ~$0.17), replacing "oss-20b + Sol, about $0.05", which was miscosted.
2. Trap results reported as counts; within-task gaps between models called real only above ~20 points.
3. Temperature left at host defaults; a temperature-0 control added (now on GLM-5.3-Flash, see 7).
4. tl05: the key is `lookup_employee`. Relabelled from contested to hard; asking instead is its own error type, `asked_instead`, on every first-step item.
5. Kinds fixed by rule (clear = no trap, hard = at least one trap, contested = key accepts two readings) and checked by `build_items.py`. 16 sample items moved from clear to hard, including inv02, which has four traps. Results are reported per kind.
6. Sol runs once per item instead of three times (~$2.00 → ~$0.67 expected). The cascades use its single answer.
7. Llama 3.1 8B (July 2024; Groq no longer lists a self-serve price for it) replaced by GLM-5.3-Flash (MIT open weights, August 2026), pinned to Z.ai at $0.15/$0.50. It is a mid-priced rung, not the cheapest; gpt-oss-20b is now the cheapest model in the ladder.
