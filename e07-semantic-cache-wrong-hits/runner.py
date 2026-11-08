"""Resumable single-query embedding runs with an exclusive writer lock."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from common import HERE, MODELS, atomic_json, digest, read_jsonl, validate_vector
from freeze import check
from run import fixture_vector


def load_key():
    """Read a small dotenv subset without logging secret contents."""
    values = {}
    for path in (HERE.parent / ".env", HERE / ".env"):
        if path.exists():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                name, separator, value = line.strip().partition("=")
                if separator and not name.startswith("#"):
                    values[name.strip()] = value.strip().strip("'\"")
    key = os.environ.get("OPENAI_API_KEY") or values.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY in the environment or an ignored .env file.")
    return key


def api_embed(text, key):
    payload = json.dumps({"model": MODELS["api"]["name"], "input": text, "encoding_format": "float"}).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings", data=payload,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        # Avoid serialising provider response bodies or request headers.
        raise RuntimeError(f"Embedding request failed with HTTP {error.code}. Resume to retry.") from None
    except (OSError, ValueError):
        raise RuntimeError("Embedding request failed. No secret or response body was logged.") from None
    return result["data"][0]["embedding"], result["model"], result.get("usage", {}).get("total_tokens")


def execute(model, dry_run=False, estimate=False):
    items = read_jsonl(HERE / "items.jsonl")
    cache = read_jsonl(HERE / "cache.jsonl")
    jobs = sorted({entry["text"] for entry in cache} | {item["source"] for item in items})
    jobs += [item["query"] for item in items]
    if len(jobs) != len(set(jobs)):
        raise ValueError("Query texts overlap cache/source texts.")
    if estimate:
        upper = sum(len(text.encode("utf-8")) for text in jobs)
        print(json.dumps({"unique_texts": len(jobs), "conservative_token_upper_bound": upper,
                          "assumed_usd_per_million": 0.02,
                          "one_pass_cost_upper_usd": upper * 0.02 / 1_000_000,
                          "two_pass_allowance_usd": upper * 0.04 / 1_000_000}, indent=2))
        return
    frozen = None if dry_run else check()
    if model == "api" and not dry_run:
        upper_cost = sum(len(text.encode("utf-8")) for text in jobs) * 0.04 / 1_000_000
        if upper_cost > 2:
            raise ValueError("The two-pass API estimate exceeds $2. Tej must review the budget before proceeding.")
    if not dry_run:
        if any(importlib.metadata.version(name) != version for name, version in frozen["packages"].items()):
            raise ValueError("Installed dependency versions differ from the freeze.")
    actual_model = "fixture" if dry_run else model
    spec = dict(MODELS[actual_model] if dry_run else frozen["models"][model])
    base = HERE / "development/full-fixture" / digest(HERE / "cache.jsonl")[:12] if dry_run else HERE / "results"
    root = base / actual_model
    identity = {"spec": spec, "items_sha256": digest(HERE / "items.jsonl"),
                "cache_sha256": digest(HERE / "cache.jsonl"),
                "freeze_sha256": None if dry_run else digest(HERE / "FREEZE.json")}
    root.mkdir(parents=True, exist_ok=True)
    lock = HERE / ".run.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Another run owns .run.lock. Remove a stale lock only after checking its PID.") from None
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(str(os.getpid()))
        manifest = root / "manifest.json"
        if manifest.exists() and json.loads(manifest.read_text())["identity"] != identity:
            raise ValueError("Run identity changed. Use a separate output directory or restore frozen inputs.")
        if not manifest.exists():
            atomic_json(manifest, {"identity": identity, "started_utc": datetime.now(timezone.utc).isoformat(),
                                   "platform": platform.platform(), "processor": platform.processor(),
                                   "status": "incomplete"})
        key = load_key() if actual_model == "api" else None
        encoder = None
        if actual_model == "local":
            import torch
            from sentence_transformers import SentenceTransformer
            torch.set_num_threads(spec["torch_threads"])
            encoder = SentenceTransformer(spec["name"], revision=spec["revision"], device=spec["device"])
        records = []
        for text in jobs:
            fingerprint = hashlib.sha256(json.dumps([spec, text], sort_keys=True).encode()).hexdigest()
            path = root / "embeddings" / (fingerprint + ".json")
            if path.exists():
                row = json.loads(path.read_text(encoding="utf-8"))
                if row["text"] != text or row["spec"] != spec:
                    raise ValueError("Cached embedding identity mismatch.")
            else:
                start = time.perf_counter()
                tokens, returned = None, spec["name"]
                if actual_model == "api":
                    try:
                        vector, returned, tokens = api_embed(text, key)
                    except RuntimeError:
                        failure_path = root / "failures.json"
                        failures = json.loads(failure_path.read_text()) if failure_path.exists() else []
                        failures.append({"text_sha256": fingerprint,
                                         "utc": datetime.now(timezone.utc).isoformat()})
                        atomic_json(failure_path, failures)
                        raise
                    if returned != spec["name"]:
                        raise ValueError("Provider returned an unexpected model identity.")
                elif encoder is not None:
                    vector = encoder.encode(text, normalize_embeddings=False).tolist()
                else:
                    vector = fixture_vector(text)
                elapsed = (time.perf_counter() - start) * 1000
                validate_vector(vector, spec["dimensions"])
                failure_path = root / "failures.json"
                failures = json.loads(failure_path.read_text()) if failure_path.exists() else []
                attempts = 1 + sum(row["text_sha256"] == fingerprint for row in failures)
                row = {"text": text, "spec": spec, "vector": vector, "milliseconds": elapsed,
                       "returned_model": returned, "tokens": tokens,
                       "utc": datetime.now(timezone.utc).isoformat(), "attempts": attempts}
                atomic_json(path, row)
            validate_vector(row["vector"], spec["dimensions"])
            records.append(row)
        atomic_json(root / "embeddings.json", records)
        manifest_data = json.loads(manifest.read_text())
        manifest_data.update(status="complete", distinct_embeddings=len(records),
                             completed_utc=datetime.now(timezone.utc).isoformat())
        atomic_json(manifest, manifest_data)
        print(f"Completed {len(records)} distinct embeddings in {root}.")
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("local", "api"), default="local")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    args = parser.parse_args()
    try:
        execute(args.model, args.dry_run, args.estimate)
    except (ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
