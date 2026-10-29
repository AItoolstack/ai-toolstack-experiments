"""E06: send every item to one model REPEATS times and save each raw answer.

Standard library only. Resumable: rerun the same command and it skips calls already saved.
Scoring happens later, in analyse.py, so a scoring fix never needs a new run.

Examples:
    python run.py --model oss-20b --workers 4
    python run.py --model sol --items items_samples.jsonl --workers 4
    python run.py --model luna --dry-run          # scripted replies, no network, no key

Keys (OPENAI_API_KEY, OPENROUTER_API_KEY) come from the environment or a .env file next to this
script. They are never printed or saved. See .env.example.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import (
    HERE,
    MODEL_REPEATS,
    MODELS,
    REASONING_EFFORT,
    load_items,
    load_tools,
    messages_for,
    read_jsonl,
    results_dir,
)

URLS = {
    "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
}
MAX_TOKENS = 2000  # room for low-effort reasoning plus the answer; finish_reason "length" is recorded
RUNNER_VERSION = "v2"
RESPONSES_URL = "https://api.openai.com/v1/responses"


class StopRun(Exception):
    """A spending limit or a fatal API error: stop cleanly, keep what was saved."""


def load_key(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    for env in (HERE / ".env", Path.cwd() / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8-sig").splitlines():
                key, sep, value = line.strip().partition("=")
                if sep and key.strip() == name:
                    return value.strip().strip('"').strip("'")
    sys.exit(f"{name} not found in the environment or a .env file.")


def request_body(spec: dict, item: dict, tools: list[dict]) -> dict:
    if spec["provider"] == "openai":
        body = {"model": spec["model"], "input": messages_for(item), "max_output_tokens": MAX_TOKENS, "store": False}
        if spec["reasoning"]:
            body["reasoning"] = {"effort": REASONING_EFFORT}
        if item["task"] == "tool":
            # Explicit non-strict mode preserves the best-effort contract of the original pilot.
            body["tools"] = [{"type": "function", **t, "strict": False} for t in tools]
            body["tool_choice"] = "auto"
        return body
    body = {
        "model": spec["model"], "messages": messages_for(item),
        spec.get("token_limit_field", "max_completion_tokens"): MAX_TOKENS,
    }
    if "temperature" in spec:
        body["temperature"] = spec["temperature"]
    if item["task"] == "tool":
        body["tools"] = [{"type": "function", "function": t} for t in tools]
        body["tool_choice"] = "auto"
    if spec["provider"] == "openrouter":
        if spec["reasoning"]:
            body["reasoning"] = {"effort": REASONING_EFFORT}
        if spec["route"]:
            body["provider"] = {"order": [spec["route"]], "allow_fallbacks": False}
    elif spec["reasoning"]:
        body["reasoning_effort"] = REASONING_EFFORT
    return body


def safe_error(detail: str, key: str) -> str:
    detail = detail.replace(key, "[REDACTED]") if key else detail
    detail = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", detail)
    return re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", detail)[:1500]


def normalise_response(data: dict, api: str) -> dict:
    usage = data.get("usage", {})
    if data.get("error"):
        raise StopRun("API error: " + json.dumps(data["error"]))
    if api == "responses":
        output = data.get("output", [])
        if data.get("status") not in ("completed", "incomplete"):
            raise StopRun("Unexpected Responses status: " + str(data.get("status")))
        content = "".join(
            part.get("text", "")
            for message in output
            if message.get("type") == "message"
            for part in message.get("content", [])
            if part.get("type") == "output_text"
        )
        calls = [
            {"name": c["name"], "arguments": c.get("arguments") or "{}"}
            for c in output
            if c.get("type") == "function_call"
        ]
        incomplete = data.get("incomplete_details") or {}
        finish = (
            "length"
            if incomplete.get("reason") == "max_output_tokens"
            else "incomplete"
            if data.get("status") == "incomplete"
            else "tool_calls"
            if calls
            else "stop"
        )
        return {
            "content": content,
            "tool_calls": calls,
            "finish_reason": finish,
            "response_status": data.get("status"),
            "incomplete_details": data.get("incomplete_details"),
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
            "served_by": "OpenAI",
        }
    choice = data["choices"][0]
    msg = choice["message"]
    return {
        "content": msg.get("content") or "",
        "tool_calls": [
            {"name": c["function"]["name"], "arguments": c["function"].get("arguments") or "{}"}
            for c in (msg.get("tool_calls") or [])
        ],
        "finish_reason": choice.get("finish_reason"),
        "served_by": data.get("provider"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
    }


def call_api(spec: dict, key: str, item: dict, tools: list[dict], on_error=None) -> dict:
    api = "responses" if spec["provider"] == "openai" else "chat/completions"
    url = RESPONSES_URL if api == "responses" else URLS[spec["provider"]][0]
    request = urllib.request.Request(
        url,
        data=json.dumps(request_body(spec, item, tools)).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-toolstack-experiments/1.0",
        },
    )
    started = time.monotonic()
    diagnostics = []
    for attempt in range(1, 6):
        wait = 5 * attempt
        retry = False
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read())
            result = normalise_response(data, api)
            return {
                **result,
                "api": api,
                "attempts": attempt,
                "retry_errors": diagnostics,
                "latency_s": round(time.monotonic() - started, 2),
            }
        except urllib.error.HTTPError as e:
            detail = safe_error(e.read().decode(errors="replace"), key)
            error = f"HTTP {e.code}: {detail}"
            if e.code == 429:
                try:
                    wait = float(e.headers.get("retry-after") or 20) + 1
                except ValueError:
                    wait = 21
                retry = "per day" not in detail.lower() and wait <= 600
            elif e.code >= 500:
                retry = True
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            error = safe_error(f"{type(e).__name__}: {e}", key)
            retry = True
        except (ValueError, KeyError, TypeError, IndexError, StopRun) as e:
            error = safe_error(f"{type(e).__name__}: {e}", key)
        diagnostic = {"attempt": attempt, "error": error, "retrying": retry and attempt < 5}
        diagnostics.append(diagnostic)
        if on_error:
            on_error(diagnostic)
        if not retry or attempt == 5:
            raise StopRun(f"{error} (attempt {attempt}/5)")
        time.sleep(wait)


def scripted(item: dict, rng: random.Random) -> dict:
    """Dry run: returns the gold answer most of the time and a plausible wrong one otherwise."""
    right = rng.random() < (0.9 if item["kind"] == "clear" else 0.6)
    gold = item["gold"]

    def pick(v):
        if isinstance(v, dict) and "any_of" in v:
            return pick(v["any_of"][0])
        if isinstance(v, dict) and "set" in v:
            return v["set"]
        if isinstance(v, dict) and "present" in v:
            return "scripted text"
        return v

    content, calls = "", []
    if item["task"] == "invoice":
        out = {k: pick(v) for k, v in gold.items()}
        if not right:
            out["amount_due"] = out["gross_total"]
            out["due_date"] = None
        content = json.dumps(out)
    elif item["task"] == "tool":
        if gold["call"] and right:
            calls = [{"name": gold["call"], "arguments": json.dumps({k: pick(v) for k, v in gold["args"].items()})}]
        elif not gold["call"] and not right:
            calls = [{"name": "issue_refund", "arguments": json.dumps({"order_id": "FR-000000", "amount_gbp": 4.99})}]
        else:
            content = "Which order do you mean?"
    else:
        base = pick(gold["amount"])
        amount = base if right else round(base * 1.1 + 0.5, 2)
        content = json.dumps({"amount": amount, "rules_used": "2"})
    return {
        "content": content,
        "tool_calls": calls,
        "finish_reason": "stop",
        "prompt_tokens": 900,
        "completion_tokens": 250,
        "reasoning_tokens": 120,
        "latency_s": 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=list(MODELS), required=True)
    ap.add_argument("--items", default="items.jsonl")
    ap.add_argument("--repeats", type=int, help="override per-model defaults; always use 1 for pilots")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--only", help="comma-separated item ids, for a quick check before the full run")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-tag", default="", help="separate a revised run from the original pilot, e.g. v2")
    ap.add_argument("--preflight", action="store_true", help="one call per task; stored separately from scored runs")
    args = ap.parse_args()
    if args.repeats is None:
        args.repeats = MODEL_REPEATS[args.model]
    if args.repeats < 1 or args.workers < 1:
        ap.error("repeats and workers must be positive")

    spec = MODELS[args.model]
    items = list(load_items(args.items).values())
    if args.only:
        wanted = set(args.only.split(","))
        if wanted - {i["id"] for i in items}:
            ap.error("unknown item IDs in --only")
        items = [i for i in items if i["id"] in wanted]
    if args.preflight:
        items = list(
            {task: next(i for i in items if i["task"] == task) for task in sorted({i["task"] for i in items})}.values()
        )
        args.repeats = 1
    tools = load_tools()
    tag = args.run_tag + ("_preflight" if args.preflight else "")
    out_dir = results_dir(args.items, args.dry_run, tag)
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{args.model}.jsonl"
    previous = read_jsonl(out) if out.exists() else []
    config = {
        "runner_version": RUNNER_VERSION,
        "spec": spec,
        "max_tokens": MAX_TOKENS,
        "requests": [request_body(spec, i, tools) for i in load_items(args.items).values()],
        "items_sha256": hashlib.sha256((HERE / args.items).read_bytes()).hexdigest(),
    }
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    if any(r.get("config_sha256") != fingerprint for r in previous):
        ap.error("saved results use a different or legacy configuration; choose a new --run-tag")
    done = {(r["item"], r["repeat"]) for r in previous}
    todo = [(rep, it) for rep in range(args.repeats) for it in items if (it["id"], rep) not in done]
    print(f"{args.items} | {args.model} ({spec['model']}): {len(done)} saved, {len(todo)} to go", flush=True)
    if not todo:
        return

    key = None if args.dry_run else load_key(URLS[spec["provider"]][1])
    write_lock, stop, saved = threading.Lock(), threading.Event(), [0]

    with open(out, "a", encoding="utf-8") as f:

        def log_error(item, rep, diagnostic):
            record = {
                "model": args.model,
                "item": item["id"],
                "repeat": rep,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "config_sha256": fingerprint,
                **diagnostic,
            }
            with write_lock:
                with open(out_dir / f"{args.model}.errors.jsonl", "a", encoding="utf-8") as log:
                    log.write(json.dumps(record) + "\n")
                print(f"{args.model} {item['id']}: {diagnostic['error']}", flush=True)

        def work(job: tuple[int, dict]) -> None:
            rep, item = job
            if stop.is_set():
                return
            try:
                result = (
                    scripted(item, random.Random(f"6:{rep}:{item['id']}"))
                    if args.dry_run
                    else call_api(spec, key, item, tools, lambda d: log_error(item, rep, d))
                )
            except StopRun as e:
                stop.set()
                print(f"STOP {args.model} {item['id']}: {e}", flush=True)
                return
            record = {
                "item": item["id"],
                "task": item["task"],
                "repeat": rep,
                "model": args.model,
                "model_id": spec["model"],
                "runner_version": RUNNER_VERSION,
                "config_sha256": fingerprint,
                "preflight": args.preflight,
                "reasoning_effort": REASONING_EFFORT if spec["reasoning"] else None,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                **result,
            }
            with write_lock:
                f.write(json.dumps(record) + "\n")
                f.flush()
                saved[0] += 1
                if saved[0] % 30 == 0 or saved[0] == len(todo):
                    print(f"  {saved[0]}/{len(todo)}", flush=True)

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            list(pool.map(work, todo))
    if stop.is_set():
        sys.exit(1)


if __name__ == "__main__":
    main()
