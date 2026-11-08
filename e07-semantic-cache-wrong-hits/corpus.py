"""Deterministic synthetic corpus. Family IDs describe shared wording frames."""
import csv
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTEXTS = {
    "shop": ("the training shop", "the demonstration storefront", "the returns sandbox",
             "the test retailer", "the support exercise"),
    "insurance": ("the training policy", "the claims sandbox", "the demonstration insurer",
                  "the policy administration exercise", "the fictional broker"),
    "it": ("the helpdesk sandbox", "the onboarding exercise", "the test department",
           "the training network", "the demonstration service desk"),
    "knowledge": ("the classroom exercise", "the practice worksheet", "the demonstration lesson",
                  "the teaching sandbox", "the training quiz"),
    "travel": ("the travel sandbox", "the demonstration operator", "the booking exercise",
               "the training route", "the fictional transport desk"),
}

# Each family has a source, a close paraphrase, a further paraphrase, and one
# same-topic question with a different answer. All facts are supplied in the text.
FAMILIES = [
    ("shop", "refund_method",
     "The test shop sends refunds to the original card. Where will my refund go?",
     "Where does the test shop send my refund if it uses the original card?",
     "I paid by card. The test shop returns payments to that same card. What is the destination?",
     "The original card.", "The test shop issues refunds in five days. How long does a refund take?",
     "Five days."),
    ("shop", "parcel_location",
     "The test parcel is at the depot. Where is it now?",
     "Where is the test parcel currently, given that it is at the depot?",
     "Tracking puts this test package at the depot. Tell me its current location.",
     "At the depot.", "The test parcel at the depot weighs two kilograms. What does it weigh?",
     "Two kilograms."),
    ("insurance", "excess_amount",
     "This fictional policy has a £200 excess. How much is the excess?",
     "What excess applies under this fictional policy with a £200 excess?",
     "The example policy requires the claimant to bear £200. State the excess amount.",
     "£200.", "This fictional policy has a £200 excess and renews in June. When does it renew?",
     "June."),
    ("insurance", "claim_channel",
     "The example insurer accepts claims through its portal. How do I submit a claim?",
     "Which channel accepts claims for the example insurer that uses a portal?",
     "For this insurer's example process, claims go through the portal. Where should I file mine?",
     "Through the portal.", "The example insurer's portal closes for maintenance on Sundays. When is it closed?",
     "Sundays."),
    ("it", "backup_schedule",
     "The test server backs up nightly. How often does it back up?",
     "How frequently is the test server backed up if backups run nightly?",
     "Every night the sandbox server saves a backup. Tell me the backup frequency.",
     "Nightly.", "The test server backs up nightly to an external disk. Where are backups stored?",
     "On an external disk."),
    ("it", "support_hours",
     "The test helpdesk opens at 08:00. When does support open?",
     "At what time does the test helpdesk open, given its 08:00 opening time?",
     "Support staff start accepting requests at 08:00 in this exercise. When can requests begin?",
     "08:00.", "The test helpdesk opens at 08:00 and closes at 18:00. When does it close?",
     "18:00."),
    ("knowledge", "triangle_sides",
     "A triangle has three sides. How many sides does a triangle have?",
     "How many sides are there in a triangle, a three-sided shape?",
     "Count the edges of this three-sided polygon called a triangle.",
     "Three.", "A triangle has three sides and three vertices. What is a corner of a polygon called?",
     "A vertex."),
    ("knowledge", "water_freeze",
     "In this worksheet water freezes at 0 degrees Celsius. What is its freezing point?",
     "What freezing temperature does the worksheet give for water, stated as 0 degrees Celsius?",
     "The exercise lists 0 degrees Celsius as water's freezing temperature. Give that temperature.",
     "0 degrees Celsius.",
     "The worksheet uses Celsius for temperature and metres for distance. Which unit measures distance?",
     "Metres."),
    ("travel", "platform_number",
     "The demonstration train leaves from platform 6. Which platform should I use?",
     "Which platform serves the demonstration train departing from platform 6?",
     "My train in this exercise is assigned to platform 6. Tell me where to board.",
     "Platform 6.", "The demonstration train leaves platform 6 at noon. When does it depart?",
     "Noon."),
    ("travel", "boarding_document",
     "The fictional ferry requires a boarding pass. What must I show to board?",
     "Which document does the fictional ferry require if boarding needs a pass?",
     "To step onto the ferry in this exercise I must present a boarding pass. What should I have ready?",
     "A boarding pass.", "The fictional ferry requires a boarding pass and takes 40 minutes. How long is the crossing?",
     "40 minutes."),
]


def qualify(text, context, variant):
    wrappers = (
        f"For {context}, {text[0].lower() + text[1:]}",
        f"{text} This request concerns {context}.",
        f"Please answer for {context}. {text}",
        f"{text} Use the scenario for {context}.",
        f"In the exercise involving {context}, {text[0].lower() + text[1:]}",
    )
    return wrappers[variant % len(wrappers)]


def full_items():
    with (HERE / "development/sample_pairs.tsv").open(encoding="utf-8", newline="") as stream:
        seeds = list(csv.DictReader(stream, delimiter="\t"))
    items = []
    for index, seed in enumerate(seeds):
        for variant in range(6):
            item = dict(seed)
            if variant:
                context = CONTEXTS[item["domain"]][variant - 1]
                for field in ("source", "query"):
                    item[field] = qualify(item[field], context, variant - 1)
            item.update(id=f"near-{index:02d}-{variant}", label="different", provenance="synthetic",
                        family=f"near-{index:02d}")
            items.append(item)
    for index, family in enumerate(FAMILIES):
        domain, template, source, close, further, answer, other, other_answer = family
        for variant in range(12):
            # Two paraphrase distances and six contexts per family.
            context_index, distance = divmod(variant, 2)
            query = (close, further)[distance]
            left = source
            if context_index:
                context = CONTEXTS[domain][context_index - 1]
                left = qualify(left, context, context_index - 1)
                query = qualify(query, context, context_index - 1)
            items.append(dict(id=f"para-{index:02d}-{variant:02d}", type="paraphrase", domain=domain,
                              template=template, source=left, query=query, source_answer=answer,
                              query_answer=answer, why="Both request the same stated fact.",
                              label="same", provenance="synthetic", family=f"fact-{index:02d}"))
        for variant in range(6):
            left, query = source, other
            if variant:
                context = CONTEXTS[domain][variant - 1]
                left = qualify(left, context, variant - 1)
                query = qualify(query, context, variant - 1)
            items.append(dict(id=f"other-{index:02d}-{variant}", type="unrelated", domain=domain,
                              template=template, source=left, query=query, source_answer=answer,
                              query_answer=other_answer, why="Same topic, different requested fact.",
                              label="different", provenance="synthetic", family=f"fact-{index:02d}"))
    return items


def cache_entries(items):
    # Identical source questions shared by paraphrases are one actual cache entry.
    entries = {}
    for item in items:
        text = item["source"]
        if text in entries and entries[text]["answer"] != item["source_answer"]:
            raise ValueError("Conflicting answers for identical stored questions.")
        entries.setdefault(text, dict(id=f"source-{item['id']}", text=text, answer=item["source_answer"]))
    # Generated cache background. Twenty frames are repeated across fictional IDs.
    backgrounds = (
        ("Where do I upload the receipt for order {id}?", "Use the returns portal for {id}."),
        ("Which courier handles parcel {id}?", "The test courier handles {id}."),
        ("How do I exchange the shoes in order {id}?", "Use the exchange form for {id}."),
        ("Where is the invoice for purchase {id}?", "The invoice for {id} is in the test account."),
        ("Which repairer is assigned to claim {id}?", "The training repairer handles {id}."),
        ("Where is the schedule for policy {id}?", "The schedule for {id} is in the policy portal."),
        ("How do I add a bicycle to policy {id}?", "Use the amendment form for {id}."),
        ("Which team reviews the documents for claim {id}?", "The claims intake team reviews {id}."),
        ("How do I unlock test account {id}?", "Contact the access desk about {id}."),
        ("Which host runs service {id}?", "The test cluster hosts {id}."),
        ("Where is the runbook for application {id}?", "The sandbox wiki contains the runbook for {id}."),
        ("What is the maintenance window for printer {id}?", "Printer {id} is maintained on Saturdays."),
        ("What material is sample {id} made of?", "Sample {id} is copper."),
        ("Who catalogued exhibit {id}?", "The training curator catalogued {id}."),
        ("What unit is used on worksheet {id}?", "Worksheet {id} uses centimetres."),
        ("Which shelf holds reference book {id}?", "Reference book {id} is on shelf C."),
        ("Where is the pickup point for booking {id}?", "The pickup point for {id} is the test terminal."),
        ("What meal is included with ticket {id}?", "Ticket {id} includes a sandwich."),
        ("How do I amend the passenger name on reservation {id}?", "Use the booking desk for {id}."),
        ("Which gate serves the demonstration flight {id}?", "Flight {id} uses gate D."),
    )
    for index in range(1000 - len(entries)):
        question, answer = backgrounds[index % len(backgrounds)]
        ident = f"ZX-{index:04d}"
        text = "In the fictional training records, " + question.format(id=ident)
        entries[text] = dict(id=f"distractor-{index:04d}", text=text, answer=answer.format(id=ident))
    cache = sorted(entries.values(), key=lambda entry: entry["id"])
    queries = {item["query"] for item in items}
    if queries.intersection(entries):
        raise ValueError("A test query appears verbatim in the cache.")
    for item in items:
        item["acceptable_ids"] = [entry["id"] for entry in cache if entry["answer"] == item["query_answer"]]
    return cache


def validate_full(items):
    counts = Counter(item["type"] for item in items)
    expected = dict.fromkeys(("entity_id", "negation", "number_date", "scope_qualifier",
                              "direction_word_order", "actor_permission"), 30)
    expected.update(paraphrase=120, unrelated=60)
    if counts != expected or len({item["id"] for item in items}) != 360:
        raise ValueError("Full cohort counts or IDs are invalid.")
    if len({item["query"].casefold() for item in items}) != 360:
        raise ValueError("Queries must be distinct.")
    for group in counts:
        cohort = [item for item in items if item["type"] == group]
        if len({item["domain"] for item in cohort}) < 4:
            raise ValueError(f"{group} needs at least four domains.")
        for field, cap in (("domain", 0.35), ("template", 0.25)):
            if max(Counter(item[field] for item in cohort).values()) > len(cohort) * cap:
                raise ValueError(f"{group} exceeds {field} cap.")
        frames = Counter(re.sub(r"\d+", "#", item["source"].casefold()) for item in cohort)
        if max(frames.values()) > len(cohort) * 0.25:
            raise ValueError(f"{group} exceeds numeric-slot wording cap.")
        for item in cohort:
            if (item["source_answer"] == item["query_answer"]) != (item["label"] == "same"):
                raise ValueError("Label conflicts with answer key.")
