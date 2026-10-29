"""Additional fictional items, written after development pilots and before evaluation calls."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from build_items import HERE, PRIYA, build
from policies import CALCULATORS

INVOICE_FACTS = {}
RULE_FACTS = {}


def invoice(
    n,
    kind="hard",
    traps=(),
    *,
    net="125.00",
    rate="0.20",
    deposit="0",
    credit=False,
    language="en",
    number_style="uk",
    country="UK",
    day="2026-10-02",
    date_style="iso",
    terms=False,
    missing=(),
    bill_first=False,
    decoy=False,
    ocr=False,
    receipt_terms=False,
):
    ident = f"inv{n:02}"
    supplier = f"Alder Quay Workshop {n} Ltd"
    if language == "de":
        supplier = f"Falken Bucht Werkstatt {n} GmbH"
    elif language == "fr":
        supplier = f"Atelier Rive Ambre {n} SARL"
    issued = date.fromisoformat(day)
    due = issued + timedelta(days=30)
    net = Decimal(net)
    tax = (net * Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gross = net + tax
    paid = Decimal(deposit)
    sign = -1 if credit else 1
    currency = "USD" if country == "US" else "EUR" if language != "en" else "GBP"

    def money(value):
        text = f"{value:,.2f}"
        if number_style == "de":
            return text.replace(",", "_").replace(".", ",").replace("_", ".")
        if number_style == "fr":
            return text.replace(",", " ").replace(".", ",")
        return text.replace(",", "")

    def stamp(value):
        return (
            value.strftime("%m/%d/%Y" if country == "US" else "%d/%m/%Y")
            if date_style == "local"
            else value.isoformat()
        )

    words = {
        "en": ("Invoice", "Date", "Net", "Tax", "Total", "Amount due", "Due date"),
        "de": ("Rechnung", "Rechnungsdatum", "Netto", "Umsatzsteuer", "Gesamt", "Offener Betrag", "Faellig am"),
        "fr": ("Facture", "Date de facture", "Total HT", "TVA", "Total TTC", "Solde a payer", "Echeance"),
    }[language]
    title, dated, net_label, tax_label, total_label, due_label, deadline = words
    if credit:
        title = "CREDIT NOTE / GUTSCHRIFT / AVOIR"
    if ocr:
        title, total_label = "INV0ICE", "T0TAL"
    parties = [f"Supplier / issuer: {supplier}", "Bill to: Moss Lantern Studio Ltd"]
    if bill_first:
        parties.reverse()
    lines = parties + [
        f"Document country: {country}; currency {currency}",
        f"{dated}: {stamp(issued)}",
    ]
    if "invoice_number" not in missing:
        lines.insert(len(parties) + 1, f"{title} no: AQ-{n:04}")
    if "due_date" not in missing:
        lines.append(
            "Payment due on receipt"
            if receipt_terms
            else "Terms: Net 30 from invoice date"
            if terms
            else f"{deadline}: {stamp(due)}"
        )
    if decoy:
        lines.append(f"Previous invoice reference (not this document): OLD-{9000 + n}; purchase order PO-{8000 + n}")
    lines += [
        f"One workshop service, quantity 1; net line amount {money(sign * net)} {currency}",
        f"{net_label}: {money(sign * net)} {currency}",
    ]
    if "tax_total" not in missing:
        lines.append(f"{tax_label} ({Decimal(rate) * 100}%): {money(sign * tax)} {currency}")
    lines.append(f"{total_label}: {money(sign * gross)} {currency}")
    if paid:
        lines.append(f"Deposit already received: {money(paid)} {currency}")
    lines.append(f"{due_label}: {money(-gross if credit else gross - paid)} {currency}")
    gold = {
        "supplier_name": supplier,
        "invoice_number": f"AQ-{n:04}",
        "invoice_date": issued.isoformat(),
        "due_date": {"any_of": [issued.isoformat(), None]} if receipt_terms else due.isoformat(),
        "currency": currency,
        "net_total": float(sign * net),
        "tax_total": float(sign * tax),
        "gross_total": float(sign * gross),
        "amount_due": float(-gross if credit else gross - paid),
        "is_credit_note": credit,
    }
    for field in missing:
        gold[field] = None
    INVOICE_FACTS[ident] = {
        "net": sign * net,
        "tax": sign * tax,
        "gross": sign * gross,
        "due": -gross if credit else gross - paid,
        "deposit": paid,
    }
    return {
        "task": "invoice",
        "id": ident,
        "kind": kind,
        "traps": list(traps),
        "document": "\n".join(lines),
        "gold": gold,
    }


def new_invoices():
    clear = [
        invoice(
            n,
            "clear",
            net=str(100 + 13 * n),
            country="US" if n % 3 == 0 else "UK",
            rate="0.08" if n % 3 == 0 else "0.20",
        )
        for n in range(8, 19)
    ]
    return clear + [
        invoice(19, traps=["number_format", "foreign_language"], net="1234.50", language="de", number_style="de"),
        invoice(20, traps=["number_format", "foreign_language"], net="1595.00", language="fr", number_style="fr"),
        invoice(21, traps=["date_format", "computed_due_date"], day="2026-11-03", date_style="local", terms=True),
        invoice(
            22,
            traps=["date_format", "computed_due_date"],
            day="2026-03-11",
            date_style="local",
            country="US",
            terms=True,
        ),
        invoice(23, traps=["credit_note", "decoy_reference"], credit=True, decoy=True),
        invoice(24, traps=["credit_note", "number_format"], credit=True, net="1345.50", number_style="de"),
        invoice(25, traps=["party_confusion", "decoy_reference"], bill_first=True, decoy=True),
        invoice(26, traps=["party_confusion", "ocr_noise"], bill_first=True, ocr=True),
        invoice(27, traps=["ocr_noise", "missing_field"], ocr=True, missing=["due_date"]),
        invoice(28, traps=["ocr_noise", "computed_due_date"], ocr=True, day="2026-12-17", terms=True),
        invoice(29, traps=["amount_due_differs", "missing_field"], deposit="40", missing=["due_date"]),
        invoice(30, traps=["amount_due_differs", "decoy_reference"], net="345.50", deposit="100", decoy=True),
        invoice(
            31, traps=["missing_field", "date_format"], missing=["invoice_number"], day="2026-04-09", date_style="local"
        ),
        invoice(32, traps=["number_format", "foreign_language"], language="de", net="2345.75", number_style="de"),
        invoice(33, traps=["missing_field", "amount_due_differs"], missing=["invoice_number"], deposit="25"),
        invoice(34, traps=["party_confusion", "credit_note"], bill_first=True, credit=True),
        invoice(
            35,
            traps=["computed_due_date", "date_format"],
            country="US",
            day="2026-11-12",
            date_style="local",
            terms=True,
        ),
        invoice(36, "contested", traps=["missing_field"], receipt_terms=True),
    ]


def tool(n, kind, request, call=None, args=None, traps=()):
    gold = {"call": call}
    if call:
        gold["args"] = args
    return {"task": "tool", "id": f"tl{n:02}", "kind": kind, "traps": list(traps), "request": request, "gold": gold}


def event_args(title, start, end):
    return {"title": title, "start": start, "end": end, "attendee_emails": {"any_of": [{"set": [PRIYA]}, {"set": []}]}}


def new_tools():
    present = {"present": True}
    colleague = "ellie.mere@fenwickrowe.co.uk"
    now = date(2026, 11, 4)
    assert now.strftime("%A") == "Wednesday"
    tomorrow, friday, tuesday = (now + timedelta(days=d) for d in (1, 2, 6))
    assert (tomorrow.isoformat(), friday.isoformat(), tuesday.isoformat()) == ("2026-11-05", "2026-11-06", "2026-11-10")
    return [
        tool(8, "clear", "Fetch order FR-510008.", "get_order", {"order_id": "FR-510008"}),
        tool(9, "clear", "Look up Ellie Mere's work email.", "lookup_employee", {"name": "Ellie Mere"}),
        tool(
            10,
            "clear",
            f"Email {colleague}, subject 'Stock count', body 'The stock count is complete.'",
            "send_email",
            {"to": {"set": [colleague]}, "subject": present, "body": present},
        ),
        tool(
            11,
            "clear",
            "Create an IT ticket, priority P3, titled 'Label printer offline'.",
            "create_ticket",
            {"title": present, "team": "it", "priority": "P3"},
        ),
        tool(
            12,
            "clear",
            "Convert 80 GBP to EUR.",
            "convert_currency",
            {"amount": 80, "from_currency": "GBP", "to_currency": "EUR"},
        ),
        tool(
            13,
            "clear",
            f"Create 'Shelf review' on 2026-11-12 from 09:00 to 09:30 UTC. Attendee: {colleague}.",
            "create_calendar_event",
            {
                "title": "Shelf review",
                "start": "2026-11-12T09:00:00+00:00",
                "end": "2026-11-12T09:30:00+00:00",
                "attendee_emails": {"set": [colleague]},
            },
        ),
        tool(
            14,
            "clear",
            f"Find a 30-minute free slot on 2026-11-13 for {colleague}.",
            "find_free_slots",
            {"attendee_emails": {"set": [colleague]}, "date": "2026-11-13", "duration_minutes": 30},
        ),
        tool(
            15,
            "clear",
            "Search orders for alden.mere@example.com with status 'placed'.",
            "search_orders",
            {"customer_email": "alden.mere@example.com", "status": "placed"},
        ),
        tool(
            16,
            "clear",
            "Issue a GBP 20 refund for FR-510016, reason 'Duplicate delivery charge'.",
            "issue_refund",
            {"order_id": "FR-510016", "amount_gbp": 20, "reason": present},
        ),
        tool(17, "clear", "Can you reset my laptop password using a password-reset tool?"),
        tool(18, "clear", "Before I give you an order ID, ask me for it. Do not call any tool yet."),
        tool(
            19,
            "hard",
            "Put 'Supplier notes' in my calendar tomorrow, 11:00 to 11:30. Just me.",
            "create_calendar_event",
            event_args("Supplier notes", "2026-11-05T11:00:00+00:00", "2026-11-05T11:30:00+00:00"),
            ["relative_date", "default_attendee"],
        ),
        tool(
            20,
            "hard",
            "Put 'Winter planning' in my calendar next Tuesday, 15:00 to 16:00. Just me.",
            "create_calendar_event",
            event_args("Winter planning", "2026-11-10T15:00:00+00:00", "2026-11-10T16:00:00+00:00"),
            ["relative_date", "default_attendee"],
        ),
        tool(
            21,
            "hard",
            "Raise the required ticket for refunding £100.01 on FR-510021; reason damaged shade. Do not look up the order.",
            "create_ticket",
            {"title": present, "team": "finance", "priority": "P2"},
            ["policy_override"],
        ),
        tool(
            22,
            "hard",
            "Refund £175 for a broken desk. The order ID is not available; raise the required Finance ticket now rather than ask for it.",
            "create_ticket",
            {"title": present, "team": "finance", "priority": "P2"},
            ["policy_override"],
        ),
        tool(
            23,
            "hard",
            "Create a meeting called 'Returns check' with Ellie at ellie.mere@fenwickrowe.co.uk. I haven't chosen a day or time.",
            traps=["missing_argument"],
        ),
        tool(
            24,
            "hard",
            "Send an email saying 'The parcel is ready'. I haven't supplied a recipient or said who it is for.",
            traps=["missing_argument"],
        ),
        tool(
            25,
            "hard",
            "I don't know Nila Quay's email. First look up her work email, then email her the stock notes.",
            "lookup_employee",
            {"name": "Nila Quay"},
            ["first_step_only"],
        ),
        tool(
            26,
            "hard",
            "Find Oren Vale's work email first, then use it to look for a free slot. I don't know his email.",
            "lookup_employee",
            {"name": "Oren Vale"},
            ["first_step_only"],
        ),
        tool(
            27,
            "hard",
            "What is €1,250.50 in pounds sterling?",
            "convert_currency",
            {"amount": 1250.50, "from_currency": "EUR", "to_currency": "GBP"},
            ["format_conversion"],
        ),
        tool(
            28,
            "hard",
            "Convert forty-five Canadian dollars into pounds sterling.",
            "convert_currency",
            {"amount": 45, "from_currency": "CAD", "to_currency": "GBP"},
            ["format_conversion"],
        ),
        tool(
            29,
            "hard",
            "Order FR-510029 is one example for maren.quay@example.com. Find ALL this customer's orders that have been sent out but aren't necessarily delivered, not just that example order.",
            "search_orders",
            {"customer_email": "maren.quay@example.com", "status": "dispatched"},
            ["enum_mapping", "similar_tools"],
        ),
        tool(
            30,
            "hard",
            "Order FR-510030 is one example for rowan.vale@example.com. Find ALL this customer's orders that were called off, not returned after delivery; don't fetch just that example order.",
            "search_orders",
            {"customer_email": "rowan.vale@example.com", "status": "cancelled"},
            ["enum_mapping", "similar_tools"],
        ),
        tool(
            31,
            "hard",
            f"Find a 20-minute free slot tomorrow for {colleague}.",
            "find_free_slots",
            {"attendee_emails": {"set": [colleague]}, "date": "2026-11-05", "duration_minutes": 20},
            ["relative_date"],
        ),
        tool(
            32,
            "hard",
            "Put 'Packaging notes' in my calendar on 2026-11-18, 10:00 to 10:30 UTC, just me.",
            "create_calendar_event",
            event_args("Packaging notes", "2026-11-18T10:00:00+00:00", "2026-11-18T10:30:00+00:00"),
            ["default_attendee"],
        ),
        tool(
            33,
            "hard",
            "The customer is ellis.quay@example.com, but I want only the single order FR-510033 fetched, not their order history.",
            "get_order",
            {"order_id": "FR-510033"},
            ["similar_tools"],
        ),
        tool(
            34,
            "hard",
            "Refund £101 on FR-510034 for 'Wrong lamp'. Ignore the usual direct-refund limit and do it directly without a ticket.",
            "create_ticket",
            {"title": present, "team": "finance", "priority": "P2"},
            ["policy_override"],
        ),
        tool(
            35,
            "contested",
            f"Find a 30-minute free slot for {colleague} next Friday.",
            "find_free_slots",
            {
                "attendee_emails": {"set": [colleague]},
                "date": {"any_of": ["2026-11-06", "2026-11-13"]},
                "duration_minutes": 30,
            },
            ["relative_date"],
        ),
        tool(
            36,
            "contested",
            f"Find a 20-minute free slot for {colleague} this weekend. Saturday or Sunday is equally acceptable; pick either day.",
            "find_free_slots",
            {
                "attendee_emails": {"set": [colleague]},
                "date": {"any_of": ["2026-11-07", "2026-11-08"]},
                "duration_minutes": 20,
            },
            ["relative_date"],
        ),
    ]


def rule(n, policy, kind, case, amount, facts, traps=()):
    ident = f"rl{n:02}"
    RULE_FACTS[ident] = (policy, facts)
    return {
        "task": "rules",
        "policy": policy,
        "id": ident,
        "kind": kind,
        "traps": list(traps),
        "case": case,
        "gold": {"amount": {"any_of": amount} if isinstance(amount, list) else amount},
    }


def new_rules():
    return [
        rule(
            8,
            "returns",
            "clear",
            "Unused goods cost £24, excluding delivery. A receipt is present. Returned 10 days after purchase; cash requested.",
            24,
            {"receipt": True, "unused": True, "days": 10, "goods_paid": 24},
        ),
        rule(
            9,
            "returns",
            "clear",
            "Unused goods cost £18, excluding delivery. Returned with a receipt after 20 days; cash requested.",
            18,
            {"receipt": True, "unused": True, "days": 20, "goods_paid": 18},
        ),
        rule(
            10,
            "returns",
            "hard",
            "A £19.30 item was part of a £96.50 goods basket with a £9.65 basket-wide discount. The unused item is returned with a receipt after 10 days. Cash requested. Delivery was separate.",
            17.30,
            {
                "receipt": True,
                "unused": True,
                "days": 10,
                "goods_paid": "19.30",
                "basket_goods": "96.50",
                "basket_discount": "9.65",
            },
            ["derived_base", "rounding"],
        ),
        rule(
            11,
            "returns",
            "hard",
            "Unused goods actually cost £0.99 excluding delivery. Returned with a receipt after 10 days, cash.",
            0,
            {"receipt": True, "unused": True, "days": 10, "goods_paid": "0.99"},
            ["rounding", "threshold_minimum"],
        ),
        rule(
            12,
            "returns",
            "hard",
            "Unused goods actually cost £23.35 excluding delivery. Returned with a receipt after 10 days; voucher selected.",
            25.63,
            {"receipt": True, "unused": True, "days": 10, "goods_paid": "23.35", "method": "voucher"},
            ["rounding", "order_of_operations"],
        ),
        rule(
            13,
            "returns",
            "contested",
            "Unused goods cost £18 excluding delivery. Returned with a receipt after 10 days. Both cash and voucher boxes are marked on the archived form; no later clarification exists.",
            [18, 19.80],
            {"receipt": True, "unused": True, "days": 10, "goods_paid": 18, "method": "both"},
        ),
        rule(
            14,
            "gym",
            "clear",
            "Monthly membership costs £30. Cancellation has 10 days' notice, no medical evidence, and no service credit.",
            15,
            {"notice": 10, "membership_paid": 30},
        ),
        rule(
            15,
            "gym",
            "clear",
            "Monthly membership costs £40. Cancellation has 20 days' notice, no medical evidence, and no service credit.",
            20,
            {"notice": 20, "membership_paid": 40},
        ),
        rule(
            16,
            "gym",
            "hard",
            "A member paid £120 for quarterly membership plus a separate £9 locker add-on. The advertised undiscounted quarter is £150. They cancel with 10 days' notice, no medical evidence or service credit.",
            20,
            {"notice": 10, "membership_paid": 120, "quarterly": True},
            ["derived_base", "distractor_numbers"],
        ),
        rule(
            17,
            "gym",
            "hard",
            "Monthly membership actually costs £80. Cancellation has 10 days' notice. There is no medical evidence or service credit.",
            25,
            {"notice": 10, "membership_paid": 80},
            ["exception_tier"],
        ),
        rule(
            18,
            "gym",
            "hard",
            "Monthly membership costs £40 and notice is only 3 days. The cancellation is documented as medical. There is no service credit.",
            0,
            {"notice": 3, "membership_paid": 40, "medical": True},
            ["exclusion"],
        ),
        rule(
            19,
            "gym",
            "clear",
            "A £30 monthly member cancels with 45 days' notice and no medical evidence or service credit.",
            0,
            {"notice": 45, "membership_paid": 30},
        ),
        rule(
            20,
            "energy",
            "clear",
            "£100 of unpaid energy principal is 20 days late. No other entries, support plan or reminder discount apply.",
            2,
            {"days": 20, "energy_bill": 100},
        ),
        rule(
            21,
            "energy",
            "clear",
            "£200 of unpaid energy principal is 35 days late. No other entries, support plan or reminder discount apply.",
            10,
            {"days": 35, "energy_bill": 200},
        ),
        rule(
            22,
            "energy",
            "hard",
            "The bill lists £400 energy and £15 equipment hire. £350 has already been paid toward energy principal. The energy payment is 20 days late. No support plan or discount applies.",
            1,
            {"days": 20, "energy_bill": 400, "paid": 350},
            ["derived_base", "distractor_numbers"],
        ),
        rule(
            23,
            "energy",
            "hard",
            "£800 of energy principal is still unpaid at 35 days late. There is no support plan or reminder discount.",
            20,
            {"days": 35, "energy_bill": 800},
            ["exception_tier"],
        ),
        rule(
            24,
            "energy",
            "hard",
            "£200 of energy principal is unpaid at 35 days late. The account has an active vulnerability-support plan and no reminder discount.",
            0,
            {"days": 35, "energy_bill": 200, "support": True},
            ["exclusion"],
        ),
        rule(
            25,
            "energy",
            "contested",
            "£100 of energy principal was unpaid until a receipt whose timestamp is illegible: either day 28 or day 29 after the due date. No support plan or discount applies. No other evidence resolves the date.",
            [2, 5],
            {"days": [28, 29], "energy_bill": 100},
        ),
        rule(
            26,
            "parking",
            "clear",
            "A base fine of £60 is paid 10 days after issue. There are no other entries, appeal or resident credit.",
            30,
            {"days": 10, "base": 60},
        ),
        rule(
            27,
            "parking",
            "clear",
            "A base fine of £40 is paid 20 days after issue. There are no other entries, appeal or resident credit.",
            40,
            {"days": 20, "base": 40},
        ),
        rule(
            28,
            "parking",
            "hard",
            "A base fine of £23.35 is paid 10 days after issue. The payer has an approved resident credit. There are no other entries or appeal.",
            10.44,
            {"days": 10, "base": "23.35", "credit": True},
            ["rounding", "order_of_operations"],
        ),
        rule(
            29,
            "parking",
            "hard",
            "A base fine of £1.90 is paid 10 days after issue. No other entries, appeal or resident credit apply.",
            0,
            {"days": 10, "base": "1.90"},
            ["rounding", "threshold_minimum"],
        ),
        rule(
            30,
            "parking",
            "hard",
            "A notice shows a combined £75, including an itemised £15 administration fee. It is paid 10 days after issue. The old tariff on a separate sign is £90. No appeal or resident credit applies.",
            30,
            {"days": 10, "combined": 75, "admin": 15},
            ["derived_base", "distractor_numbers"],
        ),
    ]


RAIL_FACTS = {
    "rl01": {"paid": "18.40", "delay": 34, "claim_days": 3},
    "rl02": {"paid": 52, "delay": 22, "return_ticket": True, "claim_days": 1},
    "rl03": {"paid": "3.70", "delay": 17},
    "rl04": {"paid": 412, "delay": 65, "season": "monthly", "claim_days": 2},
    "rl05": {"paid": "23.35", "delay": 41, "voucher": True, "claim_days": 1},
    "rl06": {"paid": 64, "delay": 135, "return_ticket": True, "claim_days": 7},
    "rl07": {"paid": "27.50", "delay": 90, "refunded": True},
}


def options(value):
    return value["any_of"] if isinstance(value, dict) and "any_of" in value else [value]


def build_all():
    samples = copy.deepcopy(build())
    relabels = []
    for item in samples:
        original = item["kind"]
        item["kind"] = (
            "contested"
            if original == "contested" and "any_of" in json.dumps(item["gold"])
            else "hard"
            if item["traps"]
            else "clear"
        )
        if original != item["kind"]:
            relabels.append(
                {
                    "id": item["id"],
                    "old": original,
                    "new": item["kind"],
                    "reason": "Apply handover kind rule in evaluation copy; preserve original development sample.",
                }
            )
    fresh = new_invoices() + new_tools() + new_rules()
    combined = sorted(samples + fresh, key=lambda i: (("invoice", "tool", "rules").index(i["task"]), i["id"]))
    for item in combined:
        ident = item["id"]
        if ident == "inv03":
            item["kind"] = "hard"
            item["gold"]["tax_total"] = 0.0
            item["traps"].remove("missing_field")
            item["note"] = "Audit: not VAT registered supports zero tax; issuer-name forms represent the same entity."
        elif ident == "inv06":
            item["gold"]["due_date"] = None
            item["gold"]["tax_total"] = 0.0
            item["gold"]["invoice_date"] = {"any_of": ["2026-10-07", "2026-07-10"]}
            item["note"] = "Audit: numeric date convention is undeclared; receipt date is absent, so due_date is null."
        elif ident == "inv07":
            item["traps"] += ["foreign_language", "date_format"]
        elif ident == "inv36":
            item["kind"] = "hard"
            item["gold"]["due_date"] = None
        elif ident in {"tl02", "tl19", "tl20", "tl32"}:
            item["kind"] = "contested"
        elif ident == "tl07":
            item["traps"].remove("similar_tools")
        elif ident == "tl35":
            item["kind"] = "hard"
            item["gold"] = {"call": None}
            item["traps"].append("missing_argument")
        elif ident in {"rl03", "rl11", "rl29"}:
            item["traps"].remove("rounding")
    validate(combined)
    manifest = {
        "authored_date": "2026-10-29",
        "status": "BLIND_AUDITED_FREEZE_RECORDED_SEPARATELY",
        "development_ids": [i["id"] for i in samples],
        "held_out_ids": [i["id"] for i in fresh],
        "evaluation_copy_relabels": relabels,
        "sample_sha256_before_build": hashlib.sha256((HERE / "items_samples.jsonl").read_bytes()).hexdigest(),
        "counts": dict(Counter(i["task"] for i in combined)),
        "kinds": dict(Counter(i["kind"] for i in combined)),
        "trap_coverage": {
            task: dict(Counter(t for i in combined if i["task"] == task for t in i["traps"]))
            for task in ("invoice", "tool", "rules")
        },
        "limits": [
            "21 development items are not unseen. Report 81 new items separately.",
            "Template-based invoices share structure; item uncertainty does not capture template dependence.",
            "Validators were revised using earlier development pilots. This is a post-pilot frozen design.",
        ],
    }
    return combined, manifest


def validate(items):
    assert len(items) == 102 and len({i["id"] for i in items}) == 102
    assert Counter(i["task"] for i in items) == {"invoice": 36, "tool": 36, "rules": 30}
    expected = {
        "invoice": {"clear": 12, "hard": 23, "contested": 1},
        "tool": {"clear": 12, "hard": 19, "contested": 5},
        "rules": {"clear": 10, "hard": 18, "contested": 2},
    }
    for task, counts in expected.items():
        assert Counter(i["kind"] for i in items if i["task"] == task) == counts
        coverage = Counter(t for i in items if i["task"] == task for t in i["traps"])
        assert all(n >= 3 for n in coverage.values()), (task, coverage)
    for item in items:
        assert item["kind"] != "clear" or not item["traps"], item["id"]
        assert item["kind"] != "hard" or item["traps"], item["id"]
        assert item["kind"] != "contested" or "any_of" in json.dumps(item["gold"]), item["id"]
        gold = item["gold"]
        if item["task"] == "invoice":
            for key in ("invoice_date", "due_date"):
                for value in options(gold[key]):
                    if value is not None:
                        date.fromisoformat(value)
            for net, tax, gross in itertools.product(
                *(options(gold[f]) for f in ("net_total", "tax_total", "gross_total"))
            ):
                if all(v is not None for v in (net, tax, gross)):
                    assert Decimal(str(net)) + Decimal(str(tax)) == Decimal(str(gross)), item["id"]
            if gold["is_credit_note"]:
                assert gold["amount_due"] == gold["gross_total"] < 0
            if item["id"] in INVOICE_FACTS:
                facts = INVOICE_FACTS[item["id"]]
                assert facts["net"] + facts["tax"] == facts["gross"]
                assert Decimal(str(gold["amount_due"])) == facts["due"]
        elif item["task"] == "rules":
            policy, facts = ("rail", RAIL_FACTS[item["id"]]) if item["policy"] == "rail" else RULE_FACTS[item["id"]]
            calculated = set(CALCULATORS[policy](facts))
            written = {Decimal(str(v)) for v in options(gold["amount"])}
            assert calculated == written, (item["id"], calculated, written)
        elif gold["call"]:
            for key in ("start", "end", "date"):
                for value in options(gold["args"].get(key)):
                    if value is not None:
                        parsed = datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
                        assert (
                            parsed.date() >= date(2026, 11, 4)
                            if isinstance(parsed, datetime)
                            else parsed >= date(2026, 11, 4)
                        )
