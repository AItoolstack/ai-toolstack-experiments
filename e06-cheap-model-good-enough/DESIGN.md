# E06 design: is the cheap model good enough?

Status: **design for review, 25 Oct 2026. Nothing has been run against a real model.**
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
- **Tool:** relative_date ("this Friday"), default_attendee, policy_override (a refund over £100 must become a Finance ticket), missing_argument (must ask), first_step_only (look someone up before emailing them), format_conversion (€45 to amount + ISO codes), enum_mapping ("sent back" to status "returned"), similar_tools (get_order vs search_orders).
- **Rules:** derived_base (half a return fare, a season ticket's daily fare), rounding, threshold_minimum (under £1 pays nothing), order_of_operations (round, then add 10% for vouchers), exception_tier (the 120-minute tier uses the return fare), exclusion (a refunded ticket can't also claim), distractor_numbers.

## Mix
About a third clear items (any competent model should get them; a miss here is a real problem) and two thirds hard items. A small number are **contested**: two readings are defensible, and the key accepts both (for example `due_date` null or the invoice date for "payment due on receipt"). E01's first item set was too easy and every model scored 100%, so the hard share is deliberate.

## Models: a price ladder, one prompt for all
| Short name | Model | Host | $/M in | $/M out | Reasoning |
|---|---|---|---|---|---|
| llama-8b | Llama 3.1 8B Instruct | Groq via OpenRouter | 0.05 | 0.08 | none |
| oss-20b | gpt-oss-20b | Groq via OpenRouter | 0.075 | 0.30 | low |
| luna | GPT-6 Luna | OpenAI | 0.10 | 0.50 | low |
| oss-120b | gpt-oss-120b | Groq via OpenRouter | 0.15 | 0.60 | low |
| sol | GPT-6.1 Sol | OpenAI | 2.00 | 10.00 | low |

Prices checked 25 Oct 2026 on OpenRouter's endpoint list and E01's OpenAI prices. Both gpt-oss sizes run on the same host, so that pair is the cleanest size comparison. 3 repeats each at default temperature (accuracy is the point here; E01 covered consistency).

## Cascades (no extra calls)
Both are computed from the runs above, using the fallback model's answer on the same item and repeat.
1. **Check:** keep the cheap answer unless a code check fails. The checks use no answer key: JSON parses, net + tax = gross, dates valid and due ≥ issued, credit-note sign; the tool exists, required arguments present, enum values valid, times not in the past. For the rules task the only check is "a number came back", so I expect this cascade to do almost nothing there. That's a finding, not a flaw.
2. **Agreement:** run the cheap model three times and escalate when the three answers differ.

Reported: accuracy, share escalated, and cost per 1,000 items, against the large model alone.

## Cost estimate (full set, 102 items × 3 repeats × 5 models = 1,530 calls)
Prompt sizes measured on the sample items (invoice ~320 tokens, tool ~1,010 with the tool list, rules ~500), rounded up.

| Model | Input | Output (est.) | Cost | If output is 2× |
|---|---|---|---|---|
| llama-8b | 215k | 33k | $0.01 | $0.02 |
| oss-20b | 215k | 119k | $0.05 | $0.09 |
| luna | 215k | 119k | $0.08 | $0.14 |
| oss-120b | 215k | 119k | $0.10 | $0.18 |
| sol | 215k | 157k | $2.00 | $3.56 |
| **Total** | | | **~$2.25** | **~$4.00** |

Plus a pilot on the 21 sample items, one repeat, oss-20b and Sol (about $0.05), to check the prompts parse before the full run. Groq's free tier (about 200k tokens a day) is too small for this, so the gpt-oss and Llama runs go through OpenRouter credit.

## What would make the result wrong
- **I wrote the items and the key.** Before any run, a separate agent solves every item blind; each disagreement is either a key fix (logged) or becomes contested. Same method as E01's rescoring.
- **102 items is small.** With about 100 items per model, differences under roughly 10 points between two models are noise. The write-up says so and doesn't rank close models.
- **One prompt for all models.** A cheap model can sometimes be fixed with a better prompt. Not tested here; it's a fair follow-up.
- **Host effects.** Tool calling goes through each host's parser. A call returned as text instead of a tool call is counted as a failure (a real system would miss it) and reported separately, so it isn't blamed on the model alone.
- **"Cheap" depends on the host.** The same gpt-oss-20b is listed at $0.018/M input elsewhere, four times cheaper than Groq. Hosts may quantise differently, so this experiment keeps one host and mentions the spread as a limit.

## Files
- `build_items.py` writes `items_samples.jsonl` (21 items for review) and `tools.json`. The full set will be `items.jsonl`.
- `run.py` calls one model and saves raw answers (resumable, `--dry-run`, `--only`).
- `analyse.py` scores, breaks errors down by trap, and computes both cascades.
