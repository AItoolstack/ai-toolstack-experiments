<!--
E6 post draft, 31 Oct 2026. Not published. Ghost: [Draft 31 Oct], #draft-31oct, author Teja Sagiraju.
Type: Experiment (#type-experiment). Primary tag: Model choice & cost (create the hub first, style guide §2). Plus #blog.
Title (69 chars): I didn't need the expensive model. I needed to know when to call it.
meta_title (50): Cheap LLM or frontier model? Test when to escalate
meta_description (150): I tested four cheap LLMs against a frontier model on 81 tasks. Format checks caught 2 of 58 wrong answers. Asking three times caught almost all the rest.
Excerpt: A cheap model was nearly as accurate as an expensive one. The hard part was spotting its mistakes, and checking the format of its answers almost never did.
Numbers: every figure traces to analysis_frozen_20261029_heldout/summary-v2.json, trap-kind-counts.md, uncertainty.json,
or posthoc-2026-10-31.json (post-hoc figures are labelled as such in the text). Run date 29 Oct 2026.
Chart: figures/e06-cost-accuracy-2026-10-29.png (PNG, 2x) goes after "Asking three times".
-->

[GREY CALLOUT]
**The short version**
- I gave four cheap AI models and one expensive one 81 everyday tasks with known right answers. The cheap ones got 92–97% right; the expensive one 97.5%.
- Checking the shape of each answer (valid JSON, totals add up, the tool exists) caught 2 of the cheap models' 58 wrong answers.
- Running the cheap model three times and sending disagreements to the expensive model matched it, at 27–41% of its cost.
[/GREY CALLOUT]

## "I've created a ticket." It hadn't.

A support lead asks an assistant to raise a Finance ticket for a £100.01 refund. The rule in its instructions is clear: refunds over £100 go to Finance as a ticket, never directly.

The assistant, a small and cheap model called gpt-oss-20b, replied:

> I've created a high-priority (P2) ticket for the finance team to process the refund of £100.01 for order FR-510021 (reason: damaged shade). You'll receive confirmation shortly.

It hadn't. It made no tool call at all. The ticket existed only in the sentence. On a similar request it answered three times, and three times it said "I'll create a ticket" and then didn't.

That reply passed every automatic check I had written to catch a cheap model's mistakes. This post is about why, and about what did catch it.

This is experiment 6 on ai·toolstack: is a cheap model good enough, and if it isn't always, can something cheap tell you when?

## The question, and how I tested it

Most teams pick one model for the whole application. Pick a big one and every call costs more; pick a small one and you live with its mistakes. The middle path is to let a cheap model do the work and pass the doubtful cases to an expensive one. That only works if you can tell which cases are doubtful, without knowing the answer.

So I tested two ways of deciding when to escalate:

- **The check.** Keep the cheap answer unless a code check fails: the JSON parses, net plus tax equals gross, the dates are real, the tool exists, every required argument is there.
- **Agreement.** Ask the cheap model the same thing three times. If the three answers differ, send the case to the expensive model.

Both are cascades: a chain where a cheaper step hands over to a costlier one only when it has to.

The tasks were three jobs teams often give a cheap model: pull ten fields from an invoice, choose the right tool call for an operations assistant (or ask a question when something is missing), and work out a refund from a one-page written policy. Every item has one correct answer written down before any model saw it, and every answer was marked by code. There is no AI judge here, because [my last experiment](https://www.ai-toolstack.com/blog/evaluation-is-an-engineering-problem/) showed AI judges disagree with each other by up to 27 points on the same answers.

The models, cheapest first: gpt-oss-20b and gpt-oss-120b (open-weight, on Groq), GLM-5.3-Flash (open-weight, on Z.ai), GPT-6 Luna, and GPT-6.1 Sol as the expensive model and the fallback. All ran with low reasoning effort, the setting that controls how long a model "thinks" before answering. The cheap models answered every item three times; Sol once.

Before the run, a separate AI session that had never seen my answers solved all 102 items blind. Where we disagreed, I either fixed my key or rewrote the item. That changed 17 items. Then everything was frozen: items, answers, prompts, models and prices. The full run, 1,428 answers, cost $0.31 on 29 Oct 2026.

The numbers below are from the 81 items written after a small pilot; the 21 pilot items are reported separately in the repo.

## The cheap models were nearly as accurate

On their own, the four cheap models answered 92% to 97% of items correctly. Sol answered 79 of 81, 97.5%.

That gap is small, and I won't rank the models. With 81 items, a difference of a few points between two models is noise.

The mistakes were not spread evenly. Of the cheap models' 58 wrong answers, 35 were tool calls, 16 were refund amounts and 7 were invoices. The traps that worked were ordinary ones:

- **Dates said in words.** Asked for a free slot "next Friday" (the test's today was Wednesday 4 November), gpt-oss-20b chose 9 November, a Monday, all three times. It got dates like this right 6 times out of 15.
- **Rules that override the request.** The £100 refund rule above.
- **Asking instead of guessing.** When a detail was missing or ambiguous, the cheap models often made a call with their own guess instead of asking the user.
- **Minimum amounts in a policy.** Two of the policies pay or charge nothing below a set amount. gpt-oss-20b missed that in 4 of its 6 answers.

## The checks caught 2 of 58

Every one of those 58 wrong answers came back well formed. The JSON parsed. The amounts added up. The tool existed and its arguments had the right types. So the check passed 56 of them.

The two it caught were not the kind of mistake I built it for: one answer ran out of room before it finished, and one booked a meeting that ended when it started.

It shouldn't have surprised me. Format checks catch broken output, and these models no longer produce much broken output. Their mistakes are well formed and wrong: a real date that is the wrong date, a real tool with an invented order number, a confident sentence about a ticket that doesn't exist.

The ticket at the top passed for a simpler reason. My check treated any reply without a tool call as a question to the user, and a question can't be checked by code. A false claim of action fell straight through that gap.

## Asking three times did the work

The agreement cascade did what the check couldn't. When a cheap model was unsure, its three answers tended to differ, and that difference was the signal.

With agreement, every cheap model landed level with Sol:

- gpt-oss-20b: 79 of 81, escalating 10 items, $0.40 per 1,000 items
- GPT-6 Luna: 80 of 81, escalating 7, $0.41
- GLM-5.3-Flash: 77 of 81, escalating 10, $0.61
- gpt-oss-120b: 79 of 81, escalating 5, $0.62
- Sol on its own: 79 of 81, $1.51

[CHART: figures/e06-cost-accuracy-2026-10-29.png]
*Caption: Every agreement cascade landed within two items of Sol, at a quarter to two fifths of its cost.*

Those costs include all three cheap calls for every item, plus Sol whenever it was called. Luna's cascade scoring one item more than Sol is one item. It doesn't make Luna better than Sol.

It costs time as well as money. Run the three cheap calls at once and gpt-oss-20b's cascade took 0.94 seconds for a typical item, against 2.44 seconds for Sol. Run them one after another and it took 2.22 seconds. The escalated items are the slow ones, because they wait for Sol too.

And the expensive model wasn't perfect either. Sol missed two items: it filled in a due date the invoice didn't give, and it picked a date for a meeting instead of asking which Friday was meant. Both were items whose answers the blind audit had tightened, but the lesson holds: the fallback is a better guess, not the truth.

## The check I'd add

After reading the 56 wrong answers the check let through, I tried one more rule: on a tool task, if the reply makes no tool call and asks no question, escalate it. The assistant's instructions allow only three moves (call a tool, ask, or say no tool fits), so a reply that does none of the first two is either a decline or a claim it shouldn't be making.

On the same saved answers, that rule caught all 7 replies that said a ticket was created, or would be, without creating one. It also flagged 10 correct answers, all of them polite refusals to reset a laptop password. Sending those to Sol costs a fraction of a penny each.

I designed this rule after seeing the results, so it's a lead, not a finding. It would need its own test on new items.

## What the money means

At these prompt sizes, the expensive model is cheap: $1.51 per 1,000 items, about a seventh of a US cent each. If you run a few thousand items a month, use the big model and spend the effort elsewhere.

The saving matters at volume. At a million items a month, Sol alone would cost about $1,508; the agreement cascades $403 to $619. Real documents are also much longer than my test items, and cost grows with length.

So the question isn't "which model?". It's "which model for the work, and what tells me when to call the other one?". Here, the cheap model's own disagreement told me. Checking the format didn't.

## Limits

- **The items were easier than I planned.** I aimed for two thirds hard items, but the cheap models still scored over 90%, and the invoice items in particular were built from a few templates. Treat the invoice result as close to no evidence.
- **This isn't production accuracy.** The items are short, fictional and written to test specific traps.
- **One author, one AI auditor.** I wrote every item. An AI session audited them blind; no human panel did.
- **Small numbers.** 81 items. The uncertainty intervals for every cascade against Sol include no difference at all.
- **Sol ran once per item,** so its own run-to-run variation isn't measured, and it was the fallback for every cascade.
- **Different hosts.** GLM ran on a different host from the gpt-oss models, and the same model is priced differently elsewhere. Costs are list prices, not my bill.
- **Free text wasn't marked.** A correct ticket call was marked on its team and priority, not on whether its wording made sense.
- **The opening example was my choice.** Before the run I set a rule to open on the first wrong answer the check accepted, by item ID. That was an invoice date read the UK way instead of the US way. I opened on the ticket instead because it shows the failure more clearly; the invoice example is in the repo with all the others.

[WHITE CALLOUT]
**Go further**
Code: [e06-cheap-model-good-enough on GitHub](https://github.com/AItoolstack/ai-toolstack-experiments/tree/main/e06-cheap-model-good-enough)
Data: all 102 items, every saved answer, and every wrong answer the check accepted, in the same folder
Related: [My AI judges agreed with themselves. Not with each other.](https://www.ai-toolstack.com/blog/evaluation-is-an-engineering-problem/)

Which of your model's mistakes would your current checks actually catch?
[/WHITE CALLOUT]

*First published <date>.*
