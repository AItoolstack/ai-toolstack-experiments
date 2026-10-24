# ai·toolstack experiments

Small, self-contained experiments on how LLMs behave in real systems, written up in plain
language at [ai-toolstack.com](https://www.ai-toolstack.com).

Each folder stands alone: its own items, scripts, raw results and a notebook that reproduces
every number in the write-up. Scripts use the Python standard library; you bring your own API
keys in a `.env` file, which is git-ignored and never committed (see each folder's `.env.example`).

| # | Experiment | Question | Write-up |
|---|---|---|---|
| E01 | [LLM judge consistency](e01-llm-judge-consistency/) | Do AI judges agree with themselves, and with each other? | [Write-up](https://www.ai-toolstack.com/blog/evaluation-is-an-engineering-problem/) |

All documents and data in this repo are synthetic or public. Nothing comes from an employer or client.

## Licence
Code: MIT (see `LICENSE`). Items and results: CC BY 4.0. Please link back if you reuse them.
