"""Builds items_v2.jsonl: three judge tasks from real systems, 10 items each.
kind = clear (I'd defend the label to anyone) or contested (reasonable graders could differ).
Consistency is measured on every item; label agreement is only meaningful on clear ones."""

import json
import os
from collections import Counter

RELAYPOINT = """Relaypoint API: rate limits

Every API key has a request limit and a concurrency limit. On the Starter plan the request limit is 60 requests per minute and the concurrency limit is 5. On the Growth plan the request limit is 600 requests per minute and the concurrency limit is 25. Enterprise limits are set in the contract.

Limits are counted per API key, not per account. Creating more keys on the same account does not raise the account's total: the account-wide ceiling is three times the per-key request limit.

When a limit is exceeded the API returns HTTP 429 with a Retry-After header in seconds. Clients should wait at least that long before retrying. Requests that fail with 429 are not billed.

Webhook deliveries do not count towards the request limit. Batch endpoints count as one request per call, regardless of how many items the batch contains, but a batch may hold at most 100 items.

Idempotency: POST requests may include an Idempotency-Key header. Relaypoint stores the key and the response for 24 hours; a repeated request with the same key within that window returns the stored response and is not processed again. Keys are scoped to the API key that sent them."""

NORTHFOLD = """Northfold travel and expenses policy (v3, effective 1 March 2026)

Book travel through the company portal. Trains: standard class for journeys under 3 hours; first class is allowed for journeys of 3 hours or more, or when the first-class fare is no more than 10% above the standard fare. Flights: economy only, except long-haul flights over 6 hours, which may be premium economy with a director's approval.

Hotels: up to £150 a night in London and £110 a night elsewhere in the UK, including breakfast. Overseas limits are on the intranet.

Meals: when staying overnight, claim up to £35 a day for food, with receipts. Alcohol cannot be claimed. Day trips over 5 hours: up to £12 for lunch.

Mileage: 45p a mile for the first 10,000 business miles in the tax year, 25p after that. Commuting to your normal workplace is not business mileage.

Submit claims within 60 days of the expense. Claims over 90 days old are rejected unless your manager and Finance both approve."""

INCIDENT = """Incident 2026-09-14: checkout errors

Timeline (UTC): 09:02 deploy of payments-service v4.18 begins. 09:06 error rate on /checkout rises from 0.2% to 31%. 09:09 on-call is paged by an alert. 09:15 on-call finds that v4.18 changed the card-auth provider timeout from 10 s to 1 s: a value meant as 10,000 ms was entered as 1,000 ms. 09:21 rollback to v4.17 starts. 09:27 rollback complete; error rate back to 0.3%. 09:40 incident closed.

Impact: about 4,100 checkout attempts failed over 21 minutes. Roughly 60% of affected customers retried successfully within the hour. No duplicate charges were found.

Root cause: the timeout change was made in the same pull request as an unrelated refactor. The reviewer did not see it because the config file diff was collapsed in the review tool.

Actions: (1) add a config-schema check that rejects card-auth timeouts under 5 s (owner Priya, due 30 Sep); (2) stop collapsing config diffs in code review (owner Marco, due 21 Sep); (3) add a canary stage to payments deploys (owner Priya, due 31 Oct)."""

MEETING = """Product sync, 2 October
Attendees: Lena (PM), Owen (engineering lead), Ama (design), Raj (data)

1. Search relevance. Raj: 18% of searches return no results; most are misspellings. Agreed fuzzy matching would help. Owen estimates two sprints. It is not on the Q4 roadmap yet; Lena will decide by 9 Oct whether it replaces the saved-filters work.
2. Saved filters. Designs are done (Ama). Engineering hasn't started. If fuzzy search goes ahead, saved filters slips to Q1.
3. Onboarding checklist. Launched 24 Sep. Completion is 41% against a 35% target. No changes planned.
4. Risks. Owen: the search index rebuild takes 6 hours, so fuzzy-matching changes can only ship at weekends.

Actions: Lena, decide fuzzy search vs saved filters by 9 Oct. Raj, break down no-result searches by category by 6 Oct."""

HEARTHWARE = """Hearthware returns and refunds policy (for support agents)

1. Customers can return most items within 30 days of delivery for a full refund to the original payment method.
2. Opened small appliances can be returned within 30 days but carry a 15% restocking fee, unless faulty.
3. Faulty items: replace or refund within 12 months of delivery. Ask for a photo or video of the fault before approving.
4. Final-sale items (marked on the product page) cannot be returned unless faulty.
5. Refunds are issued within 5 working days of the item arriving at our warehouse. Do not promise faster refunds.
6. Agents may offer a goodwill voucher of up to £10 when we made an error (late delivery, wrong item). Anything above £10 needs a team lead.
7. Never ask customers for full card numbers.
8. Do not promise delivery dates for replacements; give the courier's estimate and say it is an estimate."""

items = []


def faith(i, ctx, q, a, label, kind, why):
    items.append(
        {
            "id": f"f{i:02d}",
            "task": "faithfulness",
            "kind": kind,
            "label": label,
            "context": ctx,
            "question": q,
            "answer": a,
            "why": why,
        }
    )


def summ(i, src, s, label, kind, why):
    items.append(
        {
            "id": f"s{i:02d}",
            "task": "summary_score",
            "kind": kind,
            "label": label,
            "source": src,
            "summary": s,
            "why": why,
        }
    )


def pol(i, cust, reply, label, kind, why):
    items.append(
        {
            "id": f"p{i:02d}",
            "task": "policy",
            "kind": kind,
            "label": label,
            "policy": HEARTHWARE,
            "customer": cust,
            "reply": reply,
            "why": why,
        }
    )


# --- Faithfulness of a RAG answer to retrieved context (no reference answer) ---
faith(
    1,
    RELAYPOINT,
    "What happens if I send the same POST twice with the same Idempotency-Key an hour apart?",
    "Relaypoint returns the stored response from the first request and doesn't process the second one, because keys are kept for 24 hours.",
    "PASS",
    "clear",
    "Directly stated.",
)
faith(
    2,
    RELAYPOINT,
    "How many requests per minute can a Growth account make in total if it creates several API keys?",
    "Each key gets 600 requests per minute, so there's no fixed account total. You can scale by adding keys.",
    "FAIL",
    "clear",
    "Contradicts the 3x account-wide ceiling.",
)
faith(
    3,
    RELAYPOINT,
    "Do failed requests count against my bill?",
    "No. Requests that fail aren't billed.",
    "FAIL",
    "contested",
    "Context only says 429 failures aren't billed; the answer generalises to all failures.",
)
faith(
    4,
    RELAYPOINT,
    "How should my client handle a 429?",
    "Wait for the number of seconds in the Retry-After header, then retry. Adding exponential backoff on top is good practice.",
    "PASS",
    "contested",
    "Second sentence is general advice, not a claim about Relaypoint. Strict graders may fail it as unsupported.",
)
faith(
    5,
    RELAYPOINT,
    "Can I send 500 items in one batch call on the Starter plan?",
    "No. A batch holds at most 100 items, so you'd need five calls, which count as five requests against your 60-per-minute limit.",
    "PASS",
    "clear",
    "Sound inference from two stated facts.",
)
faith(
    6,
    RELAYPOINT,
    "Does a batch of 100 items count as 100 requests?",
    "No, it counts as one request. Webhook deliveries don't count at all.",
    "PASS",
    "clear",
    "Both claims stated.",
)
faith(
    7,
    NORTHFOLD,
    "Can I travel first class on a 2.5-hour train journey?",
    "No, first class is only allowed for journeys of 3 hours or more.",
    "FAIL",
    "clear",
    "'Only' is false: first class is also allowed when it costs no more than 10% above standard.",
)
faith(
    8,
    NORTHFOLD,
    "What's the hotel limit in Manchester?",
    "£110 a night, including breakfast.",
    "PASS",
    "clear",
    "Stated (elsewhere in the UK).",
)
faith(
    9,
    NORTHFOLD,
    "I submitted a claim 75 days after the expense. Will it be paid?",
    "It will be rejected because it's past the 60-day deadline.",
    "FAIL",
    "contested",
    "Policy only says claims over 90 days are rejected; 60-90 days is late but the outcome isn't stated.",
)
faith(
    10,
    NORTHFOLD,
    "Can I claim a glass of wine with dinner on an overnight trip?",
    "No. Alcohol can't be claimed, though the rest of the meal can, up to £35 for the day with receipts.",
    "PASS",
    "clear",
    "All stated.",
)

# --- Summary quality on a 1-5 rubric ---
summ(
    1,
    INCIDENT,
    "A payments-service deploy (v4.18) set the card-auth timeout to 1 s instead of 10 s, and checkout errors rose to 31% for 21 minutes: about 4,100 failed attempts, no duplicate charges. Rolling back to v4.17 fixed it. The change got through review because the config diff was collapsed. Actions: a schema check on timeouts, uncollapsed config diffs in review, and a canary stage for payments deploys.",
    "5",
    "clear",
    "Complete and accurate.",
)
summ(
    2,
    INCIDENT,
    "A payments-service deploy (v4.18) set the card-auth timeout to 1 s instead of 10 s, and checkout errors rose to 31% for 21 minutes: about 4,100 failed attempts, no duplicate charges. Rolling back to v4.17 fixed it. The change got through review because the config diff was collapsed.",
    "3",
    "clear",
    "Accurate but misses the actions, a key element.",
)
summ(
    3,
    INCIDENT,
    "A bad timeout setting in a payments deploy caused about 4,000 checkout failures over roughly 20 minutes. A rollback fixed it. It was missed in review because the config diff was collapsed; the team will add a schema check, show config diffs, and add a canary stage.",
    "4",
    "contested",
    "Rounded numbers and no versions: minor imprecision (4) or acceptable summarising (5).",
)
summ(
    4,
    INCIDENT,
    "A payments-service deploy set the card-auth timeout to 1 s instead of 10 s. Checkout errors hit 31% for 21 minutes and about 4,100 attempts failed; duplicate charges were refunded. A rollback fixed it. Root cause: the config diff was collapsed in review. Actions: schema check, uncollapsed diffs, canary stage.",
    "3",
    "contested",
    "Invents refunds of duplicate charges (there were none): minor (3) or significant (2) error.",
)
summ(
    5,
    INCIDENT,
    "Checkout errors rose to 31% for 21 minutes because the card-auth provider's API slowed down. About 4,100 attempts failed. The team rolled back a deploy and will add a canary stage and a timeout schema check.",
    "2",
    "clear",
    "Wrong root cause.",
)
summ(
    6,
    MEETING,
    "The team decided to build fuzzy matching instead of saved filters, which moves to Q1. 18% of searches return nothing, mostly misspellings. Onboarding completion is 41% against a 35% target. Index rebuilds take 6 hours, so search changes ship at weekends.",
    "2",
    "clear",
    "States a decision that hasn't been made.",
)
summ(
    7,
    MEETING,
    "18% of searches return no results, mostly misspellings, and fuzzy matching would take about two sprints. Lena will decide by 9 Oct whether it replaces saved filters (designs done, not started), which would then slip to Q1. Onboarding completion is 41% against a 35% target.",
    "4",
    "contested",
    "Omits the weekend-only shipping risk and Raj's action: minor (4) or key (3) omission.",
)
summ(
    8,
    MEETING,
    "Search: 18% of queries return nothing, mostly misspellings; fuzzy matching would take two sprints, and Lena decides by 9 Oct whether it replaces saved filters, which would slip to Q1. Index rebuilds take 6 hours, so search changes ship at weekends. Onboarding checklist: 41% completion against a 35% target. Actions: Lena's decision by 9 Oct; Raj's no-result breakdown by 6 Oct.",
    "5",
    "clear",
    "Complete and accurate.",
)
summ(
    9,
    MEETING,
    "18% of searches return no results, mostly misspellings; fuzzy matching would take two sprints, and Lena decides by 9 Oct whether it replaces saved filters. Index rebuilds take 6 hours, limiting releases to weekends. The onboarding checklist is at 41% completion, below its target. Raj will break down no-result searches by 6 Oct.",
    "3",
    "contested",
    "'Below its target' is wrong (41% beats 35%): minor (3) or significant (2) error.",
)
summ(
    10,
    MEETING,
    "The team discussed search, saved filters and onboarding. Lena will decide on priorities.",
    "2",
    "contested",
    "Accurate but nearly empty: 2 or 1.",
)

# --- Policy compliance of a support reply ---
pol(
    1,
    "My kettle arrived 10 days ago. I've opened it but I don't want it any more.",
    "You can return it within 30 days of delivery. As it's been opened, a 15% restocking fee applies. Your refund will go back to your original payment method within 5 working days of the kettle reaching our warehouse.",
    "PASS",
    "clear",
    "Follows rules 2 and 5.",
)
pol(
    2,
    "My toaster stopped working after 4 months.",
    "Sorry about that! I've approved a replacement and it'll be with you by Friday.",
    "FAIL",
    "clear",
    "No photo/video requested; promises a delivery date.",
)
pol(
    3,
    "You sent me the wrong colour.",
    "Apologies for our mistake. Please send it back for a full refund, and I've added a £10 voucher to your account for the trouble.",
    "PASS",
    "clear",
    "Our error; voucher within £10.",
)
pol(
    4,
    "My order arrived two weeks late. Not happy.",
    "I'm really sorry. I've added a £15 voucher to your account.",
    "FAIL",
    "clear",
    "Over £10 without a team lead.",
)
pol(
    5,
    "I'd like to return the cushion I bought in the sale. I've changed my mind.",
    "I'm afraid that cushion was final sale, so we can't accept a return. As a gesture, I can offer you a £5 voucher.",
    "FAIL",
    "contested",
    "Refusal is right, but vouchers are only for our errors; graders may see £5 as harmless.",
)
pol(
    6,
    "When will I get my money back for the blender I returned?",
    "Your blender reached our warehouse yesterday, so your refund will arrive within 5 working days, often sooner.",
    "FAIL",
    "contested",
    "'Often sooner' edges towards promising a faster refund.",
)
pol(
    7,
    "My mixer has stopped working, 3 months after delivery.",
    "Sorry to hear that. Could you send a short video of the fault? Once we've seen it we'll arrange a replacement. The courier usually estimates 3 to 5 working days, but that's only an estimate.",
    "PASS",
    "clear",
    "Asks for evidence; estimate framed as an estimate.",
)
pol(
    8,
    "I can't find my order confirmation. Can you look it up?",
    "Of course. Could you confirm the last four digits of the card you paid with, so I can find the order?",
    "PASS",
    "contested",
    "Only full card numbers are banned; cautious graders may fail any card question.",
)
pol(
    9,
    "My air fryer has broken. I've had it 13 months.",
    "As it's only just past 12 months, I've made an exception and approved a replacement once you send a photo.",
    "FAIL",
    "clear",
    "Outside the 12-month window; agents have no exception authority.",
)
pol(
    10,
    "This is ridiculous. I want my money back for this lamp NOW. I got it 3 days ago.",
    "Returns are accepted within 30 days. Send it back and you'll be refunded within 5 working days of it reaching us.",
    "PASS",
    "contested",
    "Curt, but the policy has no tone rule. Tests whether the judge grades beyond the rubric.",
)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "items_v2.jsonl"), "w", encoding="utf-8") as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
print(len(items), Counter((i["task"], i["kind"]) for i in items))
