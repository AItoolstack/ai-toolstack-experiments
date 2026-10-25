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
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import (
    HERE,
    MODELS,
    REASONING_EFFORT,
    REPEATS,
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
    body = {"model": spec["model"], "messages": messages_for(item), "max_completion_tokens": MAX_TOKENS}
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


def call_api(spec: dict, key: str, item: dict, tools: list[dict]) -> dict:
    url, _ = URLS[spec["provider"]]
    request = urllib.request.Request(
        url,
        data=json.dumps(request_body(spec, item, tools)).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-toolstack-experiments/1.0",
        },
    )
    for attempt in range(1, 6):
        start = time.time()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read())
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code == 429:
                wait = float(e.headers.get("retry-after") or 20)
                if "per day" in detail.lower() or wait > 600:
                    raise StopRun(f"Daily limit reached. Rerun later to resume. ({detail})") from e
                time.sleep(wait + 1)
                continue
            if e.code == 402:
                raise StopRun(f"Out of credit: {detail}") from e
            if e.code >= 500:
                time.sleep(5 * attempt)
                continue
            raise StopRun(f"HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * attempt)
    else:
        raise StopRun("Gave up after 5 attempts.")
    choice = data["choices"][0]
    msg = choice["message"]
    usage = data.get("usage", {})
    calls = [
        {"name": c["function"]["name"], "arguments": c["function"].get("arguments") or "{}"}
        for c in (msg.get("tool_calls") or [])
    ]
    return {
        "content": (msg.get("content") or "")[:3000],
        "tool_calls": calls,
        "finish_reason": choice.get("finish_reason"),
        "served_by": data.get("provider"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        "latency_s": round(time.time() - start, 2),
    }


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
        amount = gold["amount"] if right else round(gold["amount"] * 1.1 + 0.5, 2)
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
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--only", help="comma-separated item ids, for a quick check before the full run")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    spec = MODELS[args.model]
    items = list(load_items(args.items).values())
    if args.only:
        wanted = set(args.only.split(","))
        items = [i for i in items if i["id"] in wanted]
    tools = load_tools()
    out_dir = results_dir(args.items, args.dry_run)
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{args.model}.jsonl"
    done = {(r["item"], r["repeat"]) for r in read_jsonl(out)} if out.exists() else set()
    todo = [(rep, it) for rep in range(args.repeats) for it in items if (it["id"], rep) not in done]
    print(f"{args.items} | {args.model} ({spec['model']}): {len(done)} saved, {len(todo)} to go", flush=True)

    key = None if args.dry_run else load_key(URLS[spec["provider"]][1])
    rng = random.Random(6)
    write_lock, stop, saved = threading.Lock(), threading.Event(), [0]

    with open(out, "a", encoding="utf-8") as f:

        def work(job: tuple[int, dict]) -> None:
            rep, item = job
            if stop.is_set():
                return
            try:
                result = scripted(item, rng) if args.dry_run else call_api(spec, key, item, tools)
            except StopRun as e:
                stop.set()
                print(e)
                return
            record = {
                "item": item["id"],
                "task": item["task"],
                "repeat": rep,
                "model": args.model,
                "model_id": spec["model"],
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


if __name__ == "__main__":
    main()
