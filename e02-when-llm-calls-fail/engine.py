"""Deterministic, key-free recovery simulation. Time/cost are proxies, not live measurements."""

from __future__ import annotations

import copy
import hashlib
import itertools

from e2core import canonical, default_response, detect, historical


def uniform(*parts) -> float:
    # 53 random bits: exactly representable in a binary64 mantissa, always < 1.
    value = int.from_bytes(hashlib.sha256(canonical(parts).encode()).digest()[:8], "big") >> 11
    return value / 2**53


def scenarios(cfg):
    yield {"id": "control", "regime": "control", "rate": 0.0, "failure": None}
    for regime, rate, kind in itertools.product(cfg["regimes"], cfg["rates"], cfg["failure_types"]):
        yield {"id": f"{regime}-{int(rate * 100):02d}-{kind}", "regime": regime, "rate": rate, "failure": kind}


def should_inject(scenario, seed, ident, track, role, attempt):
    rate, regime = scenario["rate"], scenario["regime"]
    if regime == "control":
        return False
    if regime == "independent":
        return uniform(seed, ident, track, role, attempt) < rate
    if regime not in {"persistent_primary", "persistent_shared"}:
        raise ValueError(regime)
    if role == "primary" or regime == "persistent_shared":
        return uniform(seed, ident, track, "primary", 0) < rate
    return uniform(seed, ident, track, "fallback", 0) < rate


def corrupt(source, kind, task):
    row = copy.deepcopy(source)
    if kind in {"rate_limit", "timeout"}:
        row.update(content="", tool_calls=[], finish_reason=None)
        row["transport_error"] = kind
    elif kind == "cutoff":
        row["finish_reason"] = "length"
    elif kind == "malformed_json":
        if task == "tool":
            name = (row.get("tool_calls") or [{"name": "get_order"}])[0]["name"]
            row.update(content="", tool_calls=[{"name": name, "arguments": '{"broken":'}])
        else:
            row.update(content='{"broken":', tool_calls=[])
        row["finish_reason"] = "stop"
    elif kind == "empty":
        row.update(content="", tool_calls=[], finish_reason="stop")
    else:
        raise ValueError(kind)
    return row


def attempt_event(task, source, model, role, index, injected, cfg, ref):
    """No key available here; detector sees only response shape and task type."""
    row = corrupt(source, injected, task) if injected else source
    native = detect(task, source)
    observed = row.get("transport_error") or detect(task, row)
    successful_cost = historical.cost_usd(model, source["prompt_tokens"], source["completion_tokens"])
    low = high = successful_cost
    seconds = source["latency_s"]
    if injected == "rate_limit":
        seconds, low = cfg["rate_limit_seconds"], 0.0
    elif injected == "timeout":
        seconds, low = cfg["timeout_seconds"], 0.0
    elif injected == "cutoff":
        low = high = historical.cost_usd(model, source["prompt_tokens"], cfg["cutoff_output_tokens"])
    return {
        "role": role,
        "model": model,
        "source_repeat": source["repeat"],
        "attempt": index,
        "source": ref,
        "injected": injected,
        "native_fault": native,
        "observed_failure": observed,
        "seconds": seconds,
        "cost_low_usd": low,
        "cost_high_usd": high,
        "accepted_response_usd": successful_cost if observed is None else 0.0,
    }


def simulate(
    task, ident, track, seed, scenario, design, variant, primary, fallback, refs, cfg, injection_schedule=None
):
    """Recovery gets no gold labels and no scorer. A saved wrong answer can be accepted."""
    if design not in cfg["designs"]:
        raise ValueError(design)
    schedule = injection_schedule or should_inject
    events, backoff = [], 0.0
    output = None
    for index in range(cfg["primary_attempt_limits"][design]):
        if index:
            backoff += cfg["backoff_seconds"][index - 1]
        kind = scenario["failure"] if schedule(scenario, seed, ident, track, "primary", index) else None
        event = attempt_event(task, primary, cfg["primary"], "primary", index, kind, cfg, refs[0])
        events.append(event)
        if event["observed_failure"] is None:
            output = {"kind": "source", "model": cfg["primary"], "repeat": track}
            break
    if output is None and design == "fallback":
        kind = scenario["failure"] if schedule(scenario, seed, ident, track, "fallback", 0) else None
        event = attempt_event(task, fallback, cfg["fallback"], "fallback", 0, kind, cfg, refs[1])
        events.append(event)
        if event["observed_failure"] is None:
            output = {"kind": "source", "model": cfg["fallback"], "repeat": 0}
    if output is None:
        output = (
            {"kind": "default", "variant": variant}
            if design in {"default", "retry"}
            else {"kind": "unavailable", "message": "Couldn't check. No result is available."}
        )
    return {
        "item": ident,
        "task": task,
        "track": track,
        "seed": seed,
        "scenario": scenario["id"],
        "design": design,
        "variant": variant,
        "events": events,
        "output": output,
        "status": "couldnt_check" if output["kind"] == "unavailable" else "completed",
        "calls": len(events),
        "backoff_seconds": backoff,
        "latency_seconds": backoff + sum(e["seconds"] for e in events),
        "cost_low_usd": sum(e["cost_low_usd"] for e in events),
        "cost_high_usd": sum(e["cost_high_usd"] for e in events),
        "accepted_response_usd": sum(e["accepted_response_usd"] for e in events),
    }


def response_for(record, data):
    output = record["output"]
    if output["kind"] == "unavailable":
        return {"content": output["message"], "tool_calls": [], "finish_reason": None}
    if output["kind"] == "default":
        return default_response(record["task"], record["variant"])
    return data.runs[output["model"]][record["item"], output["repeat"]]
