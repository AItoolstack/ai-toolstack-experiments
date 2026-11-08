# E02: notes for readers of the write-up

The write-up: [The invoice said £244.80. Why did the AI tool show £0?](https://www.ai-toolstack.com/blog/llm-call-fails-retry-fallback-or-say-so/) (published 12 Nov 2026).

## Which file to read

- **Start with [README-RESULTS.md](README-RESULTS.md)**, then [FULL-RESULTS.md](FULL-RESULTS.md) and [RESULTS.md](RESULTS.md) (every claim mapped to its file and field).
- [README.md](README.md), [DESIGN.md](DESIGN.md) and [REVIEW-CHECKLIST.md](REVIEW-CHECKLIST.md) are kept byte-for-byte as part of the approved, hash-pinned snapshot (`FREEZE.json`, `APPROVAL.json`). That's why README.md still says no full evaluation has run: it describes the moment before the run. Editing it would break `python freeze.py --check`.

## Names in the post and in this folder

| In the post | In the code and results |
| --- | --- |
| Fill in a result | `default` |
| Try again | `retry` |
| Use a backup | `fallback` |
| Flag it | `say_so` |
| Run (2,430 per rule) | replay |
| Each request: 1-in-5 chance of timing out | `independent-20-timeout` |
| Main AI down for the whole task: 1 in 5 tasks | `persistent-primary` scenario at 20% |

## The post's figures

The two figures in the post were redrawn for the site's style from `analysis/heldout/summary.json`. The numbers are the same as in this folder; `figures-post/` keeps the original generated figures and `FIGURE-CAPTIONS.md` their captions.

## A limit worth knowing

Part of the backup rule's advantage is that the backup model was simply more accurate on these tasks. The main model (`oss-20b`) answered 223 of 243 held-out responses correctly (74–75 of 81 per saved run); the backup (`sol`) answered 79 of 81. Source: `../e06-cheap-model-good-enough/FULL-RESULTS-2026-10-29.md`, per-model table. So "use a backup" beating "flag it" on right answers is partly a better-model effect, not only a recovery effect.

Other limits are in [README-RESULTS.md](README-RESULTS.md): failure rates are assumed, retries reuse saved answers, times and costs are modelled, and nothing here measures how often real providers fail.
