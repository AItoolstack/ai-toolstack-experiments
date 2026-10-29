"""Fictional evaluation policies and independent Decimal calculators. Not real-world advice."""

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from build_items import RAIL_POLICY, RULES_QUESTION

POLICIES = {
    "rail": (RAIL_POLICY, RULES_QUESTION),
    "returns": (
        """Alder Quay fictional shop: refunds policy
1. For unused goods returned with a receipt within 30 elapsed days of purchase, refund the amount actually paid for the goods. Otherwise no standard refund is due.
2. Faulty goods with a receipt returned within 90 elapsed days receive the same refund even if used. This overrides rule 1's unused condition and 30-day limit.
3. Delivery charges are never refunded. When a basket-wide discount applies, allocate it to each item in proportion to that item's share of the undiscounted goods total. Ignore current catalogue prices.
4. Round the goods refund down to the nearest 10p. If that rounded amount is below £1, pay nothing.
5. Cash is the normal method. A customer may select a voucher instead: multiply the amount after rule 4 by 110%, then round to the nearest penny, with half pennies rounded up.
6. If both cash and voucher are marked on an archived form, this policy specifies no precedence. Either recorded choice may be used until the customer clarifies.
7. All periods include their stated final day. These rules are the entire fictional policy.""",
        "How much refund is payable under this policy, in pounds? If nothing is payable, give 0.",
    ),
    "gym": (
        """Bramble Hall fictional gym: cancellation fee policy
1. A cancellation with at least 30 elapsed days' notice has a £0 fee. With less notice, the fee is 50% of the monthly membership price actually paid.
2. For a prepaid quarter, obtain the monthly membership price by dividing the quarterly membership payment by 3. Locker add-ons and advertised undiscounted prices are not membership payments.
3. A documented medical cancellation has a £0 fee, regardless of notice or payment type.
4. For all other short-notice cancellations, cap the fee from rule 1 at £25.
5. Round the capped fee down to the nearest 10p. If that rounded amount is below £1, charge nothing.
6. A recorded service credit reduces the amount after rule 5 by 10%. Round the resulting fee to the nearest penny, with half pennies rounded up.
7. No other charges or discounts apply.""",
        "What cancellation fee is due, in pounds? If no fee is due, give 0.",
    ),
    "energy": (
        """Copper Mere fictional energy supplier: late charge policy
1. A bill paid at most 14 elapsed days after its due date has no late charge. At 15–28 days late charge 2% of the unpaid energy principal. At 29 days or later charge 5%.
2. Energy principal means energy charges on the bill minus energy-principal payments already made. Exclude equipment hire, reminder fees and other non-energy entries. Never use the original total when part has been paid.
3. An account on an active vulnerability-support plan has no late charge, overriding the other rules.
4. Cap the percentage charge at £20.
5. Round the capped charge down to the nearest 10p. If that rounded amount is below £1, charge nothing.
6. For an account with a recorded email-reminder discount, reduce the amount after rule 5 by 10%. Round to the nearest penny, with half pennies rounded up.
7. When an archived receipt's timestamp is illegible between two stated dates, calculate using either date; the policy specifies no date-resolution rule. All stated day boundaries are inclusive.""",
        "What late charge is payable, in pounds? If no charge is due, give 0.",
    ),
    "parking": (
        """Dove Reach fictional car park: payment policy
1. A notice paid within 14 elapsed days of issue costs 50% of its base fine. Payment on days 15–28 costs the full base fine. Payment on day 29 or later costs 150% of the base fine.
2. An approved appeal cancels the fine completely, irrespective of payment date.
3. Base fine excludes separately itemised reminder or administration fees. If a notice shows only a combined total and an itemised administration fee, subtract that fee to find the base fine. No administration fee is payable in this exercise.
4. Round the amount from rule 1 down to the nearest 10p. If that rounded amount is below £1, pay nothing.
5. A registered resident with an approved resident credit pays 90% of the amount after rule 4. Round this to the nearest penny, with half pennies rounded up.
6. Day 14 and day 28 are included in their respective tiers. No further concessions apply.""",
        "What fine is payable, in pounds? If nothing is payable, give 0.",
    ),
}


def d(value):
    return Decimal(str(value))


def penny(value):
    return value.quantize(d("0.01"), rounding=ROUND_HALF_UP)


def floor_and_minimum(value):
    rounded = (value / d("0.10")).to_integral_value(rounding=ROUND_DOWN) * d("0.10")
    return rounded if rounded >= 1 else d(0)


def rail(f):
    if f.get("refunded") or f.get("claim_days", 0) > 28 or f["delay"] < 15:
        return [d(0)]
    paid = d(f["paid"])
    base = paid / d({"weekly": 10, "monthly": 40, "annual": 464}.get(f.get("season"), 1))
    if f.get("return_ticket"):
        base = paid / 2
    delay = f["delay"]
    amount = base * (d("0.25") if delay < 30 else d("0.5") if delay < 60 else d(1))
    if delay >= 120 and f.get("return_ticket"):
        amount = paid
    amount = floor_and_minimum(amount)
    return [penny(amount * (d("1.1") if f.get("voucher") else d(1)))]


def returns(f):
    eligible = f["receipt"] and (f.get("faulty", False) and f["days"] <= 90 or f["unused"] and f["days"] <= 30)
    if not eligible:
        return [d(0)]
    paid = d(f["goods_paid"])
    if "basket_discount" in f:
        paid -= d(f["basket_discount"]) * paid / d(f["basket_goods"])
    cash = floor_and_minimum(paid)
    voucher = penny(cash * d("1.1"))
    method = f.get("method", "cash")
    return [cash, voucher] if method == "both" else [voucher if method == "voucher" else cash]


def gym(f):
    if f.get("medical") or f["notice"] >= 30:
        return [d(0)]
    monthly = d(f["membership_paid"]) / (3 if f.get("quarterly") else 1)
    fee = floor_and_minimum(min(monthly / 2, d(25)))
    return [penny(fee * (d("0.9") if f.get("credit") else d(1)))]


def energy(f):
    if f.get("support"):
        return [d(0)]
    answers = []
    for days in f["days"] if isinstance(f["days"], list) else [f["days"]]:
        principal = max(d(0), d(f["energy_bill"]) - d(f.get("paid", 0)))
        charge = principal * (d(0) if days <= 14 else d("0.02") if days <= 28 else d("0.05"))
        charge = floor_and_minimum(min(charge, d(20)))
        answers.append(penny(charge * (d("0.9") if f.get("discount") else d(1))))
    return answers


def parking(f):
    if f.get("appeal"):
        return [d(0)]
    base = d(f["base"]) if "base" in f else d(f["combined"]) - d(f["admin"])
    days = f["days"]
    amount = base * (d("0.5") if days <= 14 else d(1) if days <= 28 else d("1.5"))
    amount = floor_and_minimum(amount)
    return [penny(amount * (d("0.9") if f.get("credit") else d(1)))]


CALCULATORS = {"rail": rail, "returns": returns, "gym": gym, "energy": energy, "parking": parking}
