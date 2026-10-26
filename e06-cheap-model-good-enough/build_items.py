"""E06: build the item file. Every document, company and person here is fictional.

Three tasks, each graded by code against a written answer (no LLM judge):
  invoice  - extract ten fields from a messy invoice into JSON
  tool     - pick one tool call (name + arguments) for an operations assistant, or ask / decline
  rules    - apply a short written policy to a case and give the amount payable

Kinds (rule fixed 26 Oct, checked when the file is built):
  clear     - no trap; any competent model should get it, so a miss is a real problem
  hard      - built to test at least one named trap
  contested - two readings are defensible and the key accepts both ({"any_of": [...]})
Gold values may also use {"any_of": [...]} for harmless variants (e.g. title case) on any kind.
For tool items, an argument may be {"present": true} (free text, only checked for presence) or
{"set": [...]} (a list compared without order or case).

Each item carries `traps`: the difficulty it was built to test, written down BEFORE any run,
so the error analysis can't be fitted to the results afterwards. Trap codes are in DESIGN.md.

This file holds the 21 sample items for design review. The full set is added after review.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------------------------
# Task 1: invoice extraction
# ---------------------------------------------------------------------------------------------
INVOICES = [
    {
        "id": "inv01",
        "kind": "clear",
        "traps": [],
        "document": """NORTHGATE PRINT LTD
Unit 4, Calder Park, Wakefield WF2 7AA
VAT Reg: GB 284 1193 07

INVOICE
Invoice no: NP-20417
Date: 2 October 2026
Payment due: 1 November 2026

Bill to: Harrow & Finch Studio, 18 Leeming Street, Leeds LS2 7BD

Description              Qty    Unit     Amount
A2 posters, gloss        200    1.15     230.00
Foam board mounting       12    8.50     102.00
Delivery                   1   15.00      15.00

Subtotal                                 347.00
VAT @ 20%                                 69.40
Total                                   £416.40
Amount due                              £416.40""",
        "gold": {
            "supplier_name": "Northgate Print Ltd",
            "invoice_number": "NP-20417",
            "invoice_date": "2026-10-02",
            "due_date": "2026-11-01",
            "currency": "GBP",
            "net_total": 347.00,
            "tax_total": 69.40,
            "gross_total": 416.40,
            "amount_due": 416.40,
            "is_credit_note": False,
        },
    },
    {
        "id": "inv02",
        "kind": "hard",
        "traps": ["number_format", "date_format", "computed_due_date", "foreign_language"],
        "document": """Kessler Messtechnik GmbH · Industriestraße 12 · 70565 Stuttgart
USt-IdNr. DE 811 452 903

An: Brandt Laborbedarf GmbH, Speicherstadt 4, 20457 Hamburg

RECHNUNG Nr. 2026-1187
Rechnungsdatum: 03.11.2026
Lieferdatum: 28.10.2026
Zahlungsziel: 14 Tage netto ab Rechnungsdatum

Pos.  Artikel                 Menge   Einzelpreis      Gesamt
1     Drucksensor PX-40           6        185,75    1.114,50
2     Kalibrierzertifikat         1        120,00      120,00

Summe netto                                  1.234,50 EUR
USt 19 %                                       234,56 EUR
Rechnungsbetrag                              1.469,06 EUR""",
        "gold": {
            "supplier_name": "Kessler Messtechnik GmbH",
            "invoice_number": "2026-1187",
            "invoice_date": "2026-11-03",
            "due_date": "2026-11-17",
            "currency": "EUR",
            "net_total": 1234.50,
            "tax_total": 234.56,
            "gross_total": 1469.06,
            "amount_due": 1469.06,
            "is_credit_note": False,
        },
    },
    {
        "id": "inv03",
        "kind": "contested",
        "traps": ["amount_due_differs", "computed_due_date", "missing_field"],
        "document": """Invoice

From: Ashdown Joinery (Sam Ashdown), 3 Tanner Row, York YO1 6JB
To: Mrs P. Okafor, 22 Heworth Green, York YO31 7SX

Invoice #: 0093
Date of invoice: 14/09/2026
Terms: Net 30

Fitted wardrobe, oak veneer (supply and fit)          2,850.00
Additional shelving                                     240.00
Total                                                 3,090.00
Less deposit paid 22/08/2026                         (1,000.00)
Balance due                                          £2,090.00

Not VAT registered.""",
        "gold": {
            "supplier_name": {"any_of": ["Ashdown Joinery", "Ashdown Joinery (Sam Ashdown)"]},
            "invoice_number": "0093",
            "invoice_date": "2026-09-14",
            "due_date": "2026-10-14",
            "currency": "GBP",
            "net_total": 3090.00,
            "tax_total": {"any_of": [0.0, None]},
            "gross_total": 3090.00,
            "amount_due": 2090.00,
            "is_credit_note": False,
        },
        "note": "Contested only on tax_total: 'not VAT registered' supports 0 or null.",
    },
    {
        "id": "inv04",
        "kind": "hard",
        "traps": ["credit_note", "decoy_reference"],
        "document": """CREDIT NOTE   CN-5521

Brightwater Office Supplies Ltd
40 Station Road, Reading RG1 1LX

Credit note date: 21 Oct 2026
Relates to invoice: INV-88310 (dated 30 Sep 2026)
Customer: Pellow Dental Practice

Returned: 3 x ergonomic chair (model K7) @ £149.00     £447.00
Restocking fee                                          -£44.70
Net credit                                              £402.30
VAT 20%                                                  £80.46
Total credit                                            £482.76

This amount will be offset against your next invoice.""",
        "gold": {
            "supplier_name": "Brightwater Office Supplies Ltd",
            "invoice_number": "CN-5521",
            "invoice_date": "2026-10-21",
            "due_date": None,
            "currency": "GBP",
            "net_total": -402.30,
            "tax_total": -80.46,
            "gross_total": -482.76,
            "amount_due": -482.76,
            "is_credit_note": True,
        },
    },
    {
        "id": "inv05",
        "kind": "hard",
        "traps": ["party_confusion", "ocr_noise", "computed_due_date"],
        "document": """BILL TO
Quayside Events Ltd
Unit 2 The Boatyard, Bristol BS1 6XN

INV0ICE
Supplier: Harbour Lights AV Hire Ltd
5 Wapping Wharf, Bristol BS1 4RW
VAT No GB 33O 1842 55
lnvoice No: HL-7731        Date: 09 0ct 2026
Hire period 16-18 Oct 2026

LED uplighters x 24 .................. 288.00
Wireless mics x 4 ..................... 96.00
Technician (2 days) .................. 480.00
Sub-total ............................ 864.00
VAT 20% .............................. 172.80
TOTAL DUE ......................... £1,036.80
Payment due 14 days from date of invoice.""",
        "gold": {
            "supplier_name": "Harbour Lights AV Hire Ltd",
            "invoice_number": "HL-7731",
            "invoice_date": "2026-10-09",
            "due_date": "2026-10-23",
            "currency": "GBP",
            "net_total": 864.00,
            "tax_total": 172.80,
            "gross_total": 1036.80,
            "amount_due": 1036.80,
            "is_credit_note": False,
        },
    },
    {
        "id": "inv06",
        "kind": "contested",
        "traps": ["date_format", "missing_field"],
        "document": """BRIGHTLINE SOFTWARE INC.
1200 Market St, Suite 400, San Francisco, CA 94102

Invoice: BL-INV-30992
Invoice date: 10/07/2026
Customer: Ferrow Analytics Ltd (UK)

Team plan, 12 seats
Service period Oct 7, 2026 – Oct 6, 2027                 $4,320.00
Sales tax: not applicable (export of services)
Total: USD 4,320.00

Payment due on receipt.""",
        "gold": {
            "supplier_name": "Brightline Software Inc.",
            "invoice_number": "BL-INV-30992",
            "invoice_date": "2026-10-07",
            "due_date": {"any_of": [None, "2026-10-07"]},
            "currency": "USD",
            "net_total": 4320.00,
            "tax_total": {"any_of": [0.0, None]},
            "gross_total": 4320.00,
            "amount_due": 4320.00,
            "is_credit_note": False,
        },
        "note": "US date format, confirmed by the service period. 'Due on receipt' supports null or the invoice date.",
    },
    {
        "id": "inv07",
        "kind": "hard",
        "traps": ["amount_due_differs", "number_format", "decoy_reference"],
        "document": """Atelier Verdon SARL — 14 rue des Tanneurs, 69002 Lyon
SIRET 812 334 905 00021 — TVA FR 47 812334905

FACTURE N° F-26-0412          Date : 19/10/2026
Bon de commande client : PO-4471
Client : Maison Lumière SAS, Paris

Désignation                         Qté     P.U. HT      Total HT
Abat-jour lin naturel 40 cm          25       38,00        950,00
Pied de lampe laiton                 10       64,50        645,00

Total HT                                                 1 595,00 €
TVA 20 %                                                   319,00 €
Total TTC                                                1 914,00 €
Acompte versé le 01/10/2026                               -500,00 €
Net à payer                                              1 414,00 €
Échéance : 18/11/2026""",
        "gold": {
            "supplier_name": "Atelier Verdon SARL",
            "invoice_number": "F-26-0412",
            "invoice_date": "2026-10-19",
            "due_date": "2026-11-18",
            "currency": "EUR",
            "net_total": 1595.00,
            "tax_total": 319.00,
            "gross_total": 1914.00,
            "amount_due": 1414.00,
            "is_credit_note": False,
        },
    },
]

INVOICE_FIELDS = list(INVOICES[0]["gold"])

# ---------------------------------------------------------------------------------------------
# Task 2: tool calling (native tools API)
# ---------------------------------------------------------------------------------------------
TOOL_TODAY = "Wednesday 4 November 2026, 10:15, Europe/London (GMT, UTC+00:00)"
TOOL_SYSTEM = f"""You are Helm, the operations assistant for Fenwick & Rowe, a UK online homeware retailer.
Today is {TOOL_TODAY}. The user is Priya Shah (priya.shah@fenwickrowe.co.uk), customer support lead.

Use a tool when one fits the request and you have every required argument.
If a required argument is missing or ambiguous, ask one short question instead of guessing.
If no tool fits, say so briefly.
Make at most one tool call per turn. If a request needs several steps, make only the first call.
Give datetimes in ISO 8601 with the UTC offset, in UK local time.
Policy: never issue a refund above £100.00 directly. Create a ticket for the Finance team, priority P2, instead."""

TOOLS = [
    {
        "name": "get_order",
        "description": "Fetch one order by its order ID (format FR-######).",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "search_orders",
        "description": "Search orders by customer email, optionally filtered by status.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_email": {"type": "string"},
                "status": {"type": "string", "enum": ["placed", "dispatched", "delivered", "returned", "cancelled"]},
            },
            "required": ["customer_email"],
        },
    },
    {
        "name": "issue_refund",
        "description": "Refund a customer. Amount in pounds, up to £100.00.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount_gbp": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["order_id", "amount_gbp", "reason"],
        },
    },
    {
        "name": "create_ticket",
        "description": "Raise an internal ticket for a team.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "priority": {
                    "type": "string",
                    "enum": ["P1", "P2", "P3", "P4"],
                    "description": "P1 urgent, P2 high, P3 normal, P4 low",
                },
                "team": {"type": "string", "enum": ["finance", "warehouse", "it", "customer_support"]},
                "details": {"type": "string"},
            },
            "required": ["title", "priority", "team"],
        },
    },
    {
        "name": "lookup_employee",
        "description": "Find a colleague's work email, team and manager by name.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
    {
        "name": "find_free_slots",
        "description": "Find times when all attendees are free on a date.",
        "parameters": {
            "type": "object",
            "properties": {
                "attendee_emails": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "duration_minutes": {"type": "integer"},
            },
            "required": ["attendee_emails", "date", "duration_minutes"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Create a calendar event. Attendees are work email addresses.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start": {"type": "string", "description": "ISO 8601 with offset"},
                "end": {"type": "string", "description": "ISO 8601 with offset"},
                "attendee_emails": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "start", "end", "attendee_emails"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email from the user's mailbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "array", "items": {"type": "string"}},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "convert_currency",
        "description": "Convert an amount between currencies at today's rate.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "from_currency": {"type": "string", "description": "ISO 4217 code"},
                "to_currency": {"type": "string", "description": "ISO 4217 code"},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    },
]

PRIYA = "priya.shah@fenwickrowe.co.uk"
TOOL_ITEMS = [
    {
        "id": "tl01",
        "kind": "clear",
        "traps": [],
        "request": "Can you pull up order FR-448210?",
        "gold": {"call": "get_order", "args": {"order_id": "FR-448210"}},
    },
    {
        "id": "tl02",
        "kind": "hard",
        "traps": ["relative_date", "default_attendee"],
        "request": "Put 'Q4 returns review' in my calendar for this Friday, 2 to 3pm. Just me.",
        "gold": {
            "call": "create_calendar_event",
            "args": {
                "title": {"any_of": ["Q4 returns review", "Q4 Returns Review"]},
                "start": "2026-11-06T14:00:00+00:00",
                "end": "2026-11-06T15:00:00+00:00",
                "attendee_emails": {"any_of": [{"set": [PRIYA]}, {"set": []}]},
            },
        },
    },
    {
        "id": "tl03",
        "kind": "hard",
        "traps": ["policy_override"],
        "request": "Customer on FR-447902 wants a full refund of £129.99, the lamp arrived broken. Sort it please.",
        "gold": {"call": "create_ticket", "args": {"title": {"present": True}, "priority": "P2", "team": "finance"}},
    },
    {
        "id": "tl04",
        "kind": "hard",
        "traps": ["missing_argument"],
        "request": "Refund the delivery charge on that order.",
        "gold": {"call": None},
        "note": "No order has been mentioned and the amount isn't given: the right move is a question.",
    },
    {
        "id": "tl05",
        "kind": "hard",
        "traps": ["first_step_only"],
        "request": "Book a 30-minute catch-up with Tom Okoye next Tuesday, whenever we're both free.",
        "gold": {"call": "lookup_employee", "args": {"name": "Tom Okoye"}},
        "note": "Tom's email isn't known, so the first step is lookup_employee (decided 26 Oct). The system "
        "prompt's 'ask if a required argument is missing' applies to the call being made, and lookup_employee "
        "has its one required argument (the name). Asking for his email is scored wrong and counted separately "
        "as 'asked_instead'.",
    },
    {
        "id": "tl06",
        "kind": "hard",
        "traps": ["format_conversion"],
        "request": "A customer in Dublin says the price on the Irish site was €45. What's that in pounds?",
        "gold": {"call": "convert_currency", "args": {"amount": 45, "from_currency": "EUR", "to_currency": "GBP"}},
    },
    {
        "id": "tl07",
        "kind": "hard",
        "traps": ["enum_mapping", "similar_tools"],
        "request": "Can you find everything Jo Pemberton (jo.pemb@outlook.com) has sent back to us?",
        "gold": {"call": "search_orders", "args": {"customer_email": "jo.pemb@outlook.com", "status": "returned"}},
    },
]

# ---------------------------------------------------------------------------------------------
# Task 3: rules over a short document
# ---------------------------------------------------------------------------------------------
RAIL_POLICY = """Northline Rail: Delay Repay (passenger guide, effective 1 June 2026)

1. You can claim if your train arrives at your destination station 15 minutes or more after the scheduled time, whatever caused the delay.

2. Compensation is a share of the fare paid for the delayed journey:
   - 15 to 29 minutes late: 25% of the single fare
   - 30 to 59 minutes late: 50% of the single fare
   - 60 to 119 minutes late: 100% of the single fare
   - 120 minutes or more late: 100% of the return fare if you hold a return ticket, otherwise 100% of the single fare

3. For a return ticket, the single fare is half the price paid for the return. If both legs of a return journey are delayed, each leg is claimed separately.

4. For season tickets, compensation is based on a daily fare: the price of a weekly season divided by 10, a monthly season divided by 40, or an annual season divided by 464.

5. Compensation is rounded down to the nearest 10p. If the rounded amount is below £1.00, nothing is paid.

6. Claims must be made within 28 days of the date of the journey.

7. If you decided not to travel because of disruption and asked for a refund of your unused ticket, you receive that refund instead and cannot also claim Delay Repay.

8. If you used a Railcard, compensation is based on the discounted price you actually paid.

9. Compensation is paid to the card used for the ticket. You may choose rail travel vouchers instead: vouchers are worth 110% of the cash compensation, calculated on the amount after the rounding in rule 5."""

RULES_ITEMS = [
    {
        "id": "rl01",
        "kind": "clear",
        "traps": [],
        "case": "Anna bought an off-peak single from Leeds to Hull for £18.40. Her train arrived 34 minutes late "
        "because of a signal failure. She claimed three days later and wants the money on her card.",
        "gold": {"amount": 9.20},
    },
    {
        "id": "rl02",
        "kind": "hard",
        "traps": ["derived_base", "distractor_numbers"],
        "case": "Marcus paid £52.00 for a return from York to Newcastle. The outbound train arrived 22 minutes late; "
        "the return was on time. The advance single on the same route costs £31.00. He claims the next day, cash.",
        "gold": {"amount": 6.50},
    },
    {
        "id": "rl03",
        "kind": "hard",
        "traps": ["rounding", "threshold_minimum"],
        "case": "A student with a 16-25 Railcard paid £3.70 for a single. The train arrived 17 minutes late. "
        "She claims the same day, cash.",
        "gold": {"amount": 0.00},
    },
    {
        "id": "rl04",
        "kind": "hard",
        "traps": ["derived_base"],
        "case": "Dev holds a monthly season ticket that cost £412.00. On Tuesday his evening train home arrived "
        "65 minutes late. He claims on Thursday, cash.",
        "gold": {"amount": 10.30},
    },
    {
        "id": "rl05",
        "kind": "hard",
        "traps": ["rounding", "order_of_operations"],
        "case": "Ruth paid £23.35 for a single. Her train arrived 41 minutes late. She claims the next day and "
        "chooses rail travel vouchers.",
        "gold": {"amount": 12.76},
    },
    {
        "id": "rl06",
        "kind": "hard",
        "traps": ["exception_tier"],
        "case": "Owen paid £64.00 for a return from Doncaster to London. The outbound train arrived 2 hours and "
        "15 minutes late. The return leg was 10 minutes late. He claims a week later, cash.",
        "gold": {"amount": 64.00},
    },
    {
        "id": "rl07",
        "kind": "hard",
        "traps": ["exclusion"],
        "case": "Because of a strike, Lena's 08:10 service was expected to be at least 90 minutes late, so she "
        "didn't travel and asked for a refund of her £27.50 single, which she received. She now asks for Delay "
        "Repay as well.",
        "gold": {"amount": 0.00},
    },
]

RULES_QUESTION = "How much Delay Repay should be paid for this case, in pounds? If nothing is payable, the amount is 0."


def build() -> list[dict]:
    items = []
    for it in INVOICES:
        items.append({"task": "invoice", **it})
    for it in TOOL_ITEMS:
        items.append({"task": "tool", **it})
    for it in RULES_ITEMS:
        items.append({"task": "rules", "policy": "rail", **it})
    return items


if __name__ == "__main__":
    items = build()
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for it in items:
        kind, traps = it["kind"], it["traps"]
        assert kind in ("clear", "hard", "contested"), it["id"]
        assert kind != "clear" or not traps, f"{it['id']}: a clear item has no traps"
        assert kind != "hard" or traps, f"{it['id']}: a hard item names its traps"
        assert kind != "contested" or "any_of" in json.dumps(it["gold"]), f"{it['id']}: contested needs any_of"
    with open(HERE / "items_samples.jsonl", "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    (HERE / "tools.json").write_text(json.dumps(TOOLS, indent=2), encoding="utf-8")
    print(f"{len(items)} items -> items_samples.jsonl; {len(TOOLS)} tools -> tools.json")
