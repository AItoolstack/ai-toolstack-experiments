"""E01: ask the same LLM judge the same question many times and save every verdict.

Standard library only. Resumable: rerun the same command and it skips calls already saved.

Examples:
    python run.py --items items_v2.jsonl --provider openai --model gpt-6-luna --arm default --workers 6
    python run.py --items items_v2.jsonl --provider openrouter --route groq --arm temp0 --workers 4
    python run.py --items items_v2.jsonl --arm default --dry-run     # scripted replies, no network

Keys (GROQ_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY) are read from the environment or a .env
file next to this script. They are never printed or saved. See .env.example.

If a model refuses temperature 0, the temp0 arm stops and saves the API's reply as
<name>.unsupported.json. That refusal is a result too.
"""

from __future__ import annotations

import argparse
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

from common import HERE, REPEATS, load_items, read_jsonl, results_dir, task_of

PROVIDERS = {
    # tpm: tokens per minute the runner paces itself under (Groq's free tier allows about 8,000).
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
        "max_tokens": 600,
        "tpm": 7000,
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "key": "OPENAI_API_KEY",
        "model": "gpt-6-luna",
        "max_tokens": 1000,
        "tpm": None,
    },
    # Pay-as-you-go access to open models. --route pins the host (e.g. groq), with no fallbacks.
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": "OPENROUTER_API_KEY",
        "model": "openai/gpt-oss-120b",
        "max_tokens": 600,
        "tpm": None,
    },
}
REASONING_EFFORT = "low"  # the same for every run

PASS_FAIL_JSON = 'Reply with JSON only: {"verdict": "PASS" or "FAIL", "reason": "<one short sentence>"}'
PROMPTS = {  # task -> (prompt version, system prompt)
    "reference": (
        "v1",
        (
            "You grade answers to questions against a reference answer. "
            "PASS if the answer agrees with the reference and states nothing false. "
            "FAIL if it disagrees with the reference or contains any false statement, even a minor one. "
            "Extra detail is fine if it is true. Hedging is fine if the main answer is right. " + PASS_FAIL_JSON
        ),
    ),
    "faithfulness": (
        "v2",
        (
            "You check whether an assistant's answer is faithful to the retrieved context it was given. "
            "PASS if every claim in the answer is supported by the context. "
            "FAIL if any claim is contradicted by the context or goes beyond what the context supports. "
            + PASS_FAIL_JSON
        ),
    ),
    "summary_score": (
        "v2",
        (
            "You score a summary of a source document from 1 to 5.\n"
            "5: covers what happened, the impact or key figures, causes or decisions, and actions, with no errors.\n"
            "4: one minor omission or imprecision, no factual errors.\n"
            "3: misses one key element, or has one minor factual error.\n"
            "2: has a significant factual error, or misses two or more key elements.\n"
            "1: mostly wrong or misleading.\n"
            'Reply with JSON only: {"score": <1-5>, "reason": "<one short sentence>"}'
        ),
    ),
    "policy": (
        "v2",
        (
            "You check a customer-support agent's reply against the company policy. "
            "PASS if the reply follows every rule in the policy. FAIL if it breaks any rule. " + PASS_FAIL_JSON
        ),
    ),
}


class TemperatureUnsupported(Exception):
    """The model refused temperature=0."""


class StopRun(Exception):
    """A daily limit or a fatal API error: stop cleanly, keep what was saved."""


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


def user_message(item: dict) -> str:
    task = task_of(item)
    if task == "reference":
        return f"Question: {item['question']}\nReference answer: {item['reference']}\nAnswer to grade: {item['answer']}"
    if task == "faithfulness":
        return (
            f"Retrieved context:\n{item['context']}\n\nUser question: {item['question']}\n\n"
            f"Assistant's answer: {item['answer']}"
        )
    if task == "summary_score":
        return f"Source document:\n{item['source']}\n\nSummary to score:\n{item['summary']}"
    if task == "policy":
        return f"Policy:\n{item['policy']}\n\nCustomer message: {item['customer']}\n\nAgent's reply: {item['reply']}"
    raise ValueError(f"unknown task {task!r}")


def parse_verdict(text: str, task: str) -> str | None:
    """PASS/FAIL, or '1'..'5' for summary scores. None if the reply can't be read."""
    obj = {}
    try:
        obj = json.loads(text[text.index("{") : text.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        pass
    if task == "summary_score":
        match = re.search(r"[1-5]", str(obj.get("score", "")) or text)
        return match.group(0) if match else None
    verdict = str(obj.get("verdict", "") or text).strip().upper()
    for v in ("PASS", "FAIL"):
        if verdict.startswith(v):
            return v
    return None


def call_api(prov: dict, model: str, key: str, item: dict, arm: str, route: str | None) -> dict:
    task = task_of(item)
    body = {
        "model": model,
        "messages": [{"role": "system", "content": PROMPTS[task][1]}, {"role": "user", "content": user_message(item)}],
        "max_completion_tokens": prov["max_tokens"],
    }
    if "openrouter" in prov["url"]:
        body["reasoning"] = {"effort": REASONING_EFFORT}
        if route:
            body["provider"] = {"order": [route], "allow_fallbacks": False}
    else:
        body["reasoning_effort"] = REASONING_EFFORT
    if arm == "temp0":
        body["temperature"] = 0
    request = urllib.request.Request(
        prov["url"],
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-toolstack-experiments/1.0",
        },
    )
    for attempt in range(1, 6):
        start = time.time()
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read())
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code == 400 and arm == "temp0" and "temperature" in detail.lower():
                raise TemperatureUnsupported(detail) from e
            if e.code == 429:
                wait = float(e.headers.get("retry-after") or 20)
                if "per day" in detail.lower() or wait > 600:
                    raise StopRun(f"Daily limit reached. Rerun later to resume. ({detail})") from e
                time.sleep(wait + 1)
                continue
            if e.code >= 500:
                time.sleep(5 * attempt)
                continue
            raise StopRun(f"HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * attempt)
    else:
        raise StopRun("Gave up after 5 attempts.")
    choice = data["choices"][0]
    usage = data.get("usage", {})
    content = choice["message"].get("content") or ""
    return {
        "verdict": parse_verdict(content, task),
        "raw": content[:500],
        "finish_reason": choice.get("finish_reason"),
        "served_by": data.get("provider"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        "latency_s": round(time.time() - start, 2),
    }


def scripted(item: dict, arm: str, rng: random.Random) -> dict:
    """Dry run: a fake judge that is right on clear items and wobbles on the others."""
    p_right = 1.0 if item["kind"] == "clear" else (0.85 if arm == "temp0" else 0.7)
    right = str(item["label"]).upper()
    if task_of(item) == "summary_score":
        wrong = str(max(1, int(right) - 1))
    else:
        wrong = "FAIL" if right == "PASS" else "PASS"
    return {
        "verdict": right if rng.random() < p_right else wrong,
        "raw": "scripted",
        "finish_reason": "stop",
        "prompt_tokens": 600,
        "completion_tokens": 90,
        "reasoning_tokens": 40,
        "latency_s": 0.0,
    }


class Pacer:
    """Keeps tokens per minute under a budget (only needed on Groq's free tier)."""

    def __init__(self, tpm: int | None):
        self.tpm, self.window, self.lock = tpm, [], threading.Lock()

    def wait(self) -> None:
        while self.tpm:
            with self.lock:
                now = time.time()
                self.window = [(t, n) for t, n in self.window if now - t < 60]
                if sum(n for _, n in self.window) <= self.tpm:
                    return
                pause = max(1.0, 61 - (now - self.window[0][0]))
            time.sleep(pause)

    def add(self, tokens: int) -> None:
        with self.lock:
            self.window.append((time.time(), tokens))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default="items_v2.jsonl")
    ap.add_argument("--provider", choices=list(PROVIDERS), default="groq")
    ap.add_argument("--model", help="model id; defaults to the provider's entry in PROVIDERS")
    ap.add_argument("--route", help="OpenRouter only: pin the host, e.g. groq (no fallbacks)")
    ap.add_argument("--arm", choices=["default", "temp0"], required=True)
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--workers", type=int, default=1, help="calls in flight at once (keep 1 on Groq's free tier)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = list(load_items(args.items).values())
    out_dir = results_dir(args.items, args.dry_run)
    out_dir.mkdir(exist_ok=True)
    prov = PROVIDERS[args.provider]
    model = args.model or prov["model"]
    route = f"-{args.route}" if args.route else ""
    stem = f"{args.provider}{route}_{model.replace('/', '-')}__{args.arm}"
    out = out_dir / f"{stem}.jsonl"
    done = {(r["item"], r["repeat"]) for r in read_jsonl(out)} if out.exists() else set()

    key = None if args.dry_run else load_key(prov["key"])
    rng = random.Random(1)
    todo = [(rep, it) for rep in range(args.repeats) for it in items if (it["id"], rep) not in done]
    print(f"{args.items} | {args.provider} {model} {args.arm}: {len(done)} saved, {len(todo)} to go", flush=True)

    pacer = Pacer(None if args.dry_run else prov["tpm"])
    write_lock, stop, saved = threading.Lock(), threading.Event(), [0]

    with open(out, "a", encoding="utf-8") as f:

        def work(job: tuple[int, dict]) -> None:
            rep, item = job
            if stop.is_set():
                return
            pacer.wait()
            try:
                result = (
                    scripted(item, args.arm, rng)
                    if args.dry_run
                    else call_api(prov, model, key, item, args.arm, args.route)
                )
            except TemperatureUnsupported as e:
                if not stop.is_set():
                    stop.set()
                    note = out_dir / f"{stem}.unsupported.json"
                    note.write_text(
                        json.dumps(
                            {"provider": args.provider, "model": model, "arm": args.arm, "error": str(e)}, indent=2
                        ),
                        encoding="utf-8",
                    )
                    print(f"{model} does not accept temperature=0. Saved the API's reply to {note.name}.")
                return
            except StopRun as e:
                stop.set()
                print(e)
                return
            record = {
                "item": item["id"],
                "task": task_of(item),
                "repeat": rep,
                "arm": args.arm,
                "provider": args.provider,
                "model": model,
                "reasoning_effort": REASONING_EFFORT,
                "prompt_version": PROMPTS[task_of(item)][0],
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                **result,
            }
            pacer.add((result["prompt_tokens"] or 0) + (result["completion_tokens"] or 0))
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
