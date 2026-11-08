# ai·toolstack experiments

Small, self-contained experiments on how LLMs behave in real systems, written up in plain
language at [ai-toolstack.com](https://www.ai-toolstack.com).

Each folder stands alone: its own items, scripts, raw results and the code that reproduces
every number in the write-up. Scripts use the Python standard library. E01 and E06 call model
APIs: you bring your own keys in a `.env` file, which is git-ignored and never committed (see each
folder's `.env.example`). E02 makes no API calls: it replays E06's saved answers, so it needs no keys.

| # | Experiment | Question | Write-up |
|---|---|---|---|
| E01 | [LLM judge consistency](e01-llm-judge-consistency/) | Do AI judges agree with themselves, and with each other? | [Write-up](https://www.ai-toolstack.com/blog/evaluation-is-an-engineering-problem/) |
| E06 | [Cheap models and code checks](e06-cheap-model-good-enough/) | Which incorrect answers pass simple checks, and when does fallback help? | Full run 29 Oct 2026 ([results](e06-cheap-model-good-enough/FULL-RESULTS-2026-10-29.md)); [Write-up](https://www.ai-toolstack.com/blog/when-to-call-the-expensive-model/) |
| E02 | [When an LLM call fails](e02-when-llm-calls-fail/README-RESULTS.md) | Fill in a default, retry, fall back to another model, or say "couldn't check": what reaches the user, and what does each cost? | Offline replay 1 Nov 2026 ([results](e02-when-llm-calls-fail/FULL-RESULTS.md), [notes for readers](e02-when-llm-calls-fail/WRITE-UP-NOTES.md)); [Write-up](https://www.ai-toolstack.com/blog/llm-call-fails-retry-fallback-or-say-so/) (from 12 Nov 2026) |

All documents and data in this repo are synthetic or public. Nothing comes from an employer or client.
E06 chart generation uses optional Matplotlib dependencies; its runner, analysis and tests remain standard-library only.

## Licence
Code: MIT (see `LICENSE`). Items and results: CC BY 4.0. Please link back if you reuse them.
