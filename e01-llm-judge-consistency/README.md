# E01: do LLM judges agree with themselves, and with each other?

Many teams use one AI model to mark another's work (an "LLM judge"). This experiment asks four
judges to mark the same 30 items 13 times each, and measures how often they're right, how often
they change their mind, and how often they agree with each other.

Write-up: [I asked four AI models to mark the same answers 13 times](https://www.ai-toolstack.com/blog/evaluation-is-an-engineering-problem/)

## Results in one table (v2, 13 runs per judge)

| Judge | Right on 12 clear pass/fail items | Same mark all 13 runs (of 30) | Answers passed (of 20; key says 11) | Cost per 1,000 marks | Median time |
|---|---|---|---|---|---|
| gpt-oss-120b (Groq) | 11.2 | 18 | 13.3 | $0.12 | 0.36 s |
| gpt-oss-120b, temperature 0 | 11.1 | 25 | 13.9 | $0.13 | 0.34 s |
| GPT-6 Luna (temperature 0 not allowed) | 11.1 | 22 | 8.5 | $0.09 | 1.9 s |
| GPT-6.1 Sol | 12.0 | 27 | 10.8 | $1.19 | 2.3 s |

All four judges gave the same most common mark on 12 of 18 clear items, but only 3 of 12 borderline
ones. The easy v1 test (answers checked against a reference answer) produced no changed marks at
all in 1,560 calls. Prices are list prices on 24 October 2026.

## What's here

| File | What it does |
|---|---|
| `items_v1.jsonl` | v1: 30 short answers with a reference answer (the easy control) |
| `items_v2.jsonl` | v2: 30 items across document checks, summary scores and policy checks. Built by `build_items_v2.py`; all documents are made up |
| `run.py` | Calls a judge on every item N times and saves each mark. Resumable |
| `analyse.py` | Consistency, accuracy, agreement between judges, cost and speed. Writes `summary.json` |
| `make_figures.py` | The charts and grids used in the write-up, in `figures/` |
| `reproduce.ipynb` | Runs all of the above on the saved results |
| `results_v1/`, `results_v2/` | Every raw mark: verdict, the judge's reason, tokens and timing |

## Reproduce the numbers (no keys needed)

    python analyse.py                         # v2
    python analyse.py --items items_v1.jsonl  # v1
    python make_figures.py

Python 3.10 or later. The scripts use only the standard library.

## Run it yourself

Copy `.env.example` to `.env` and add your keys (`.env` is git-ignored). Then, for example:

    python run.py --items items_v2.jsonl --provider openai --model gpt-6-luna --arm default --workers 6
    python run.py --items items_v2.jsonl --provider openrouter --route groq --arm temp0 --workers 4
    python run.py --items items_v2.jsonl --provider groq --arm default   # Groq free tier, slower

`--arm temp0` sets temperature 0; if a model refuses, the run stops and saves the API's reply as
`<name>.unsupported.json`. `--dry-run` uses scripted replies, with no key and no network. A v2 run
of 390 calls costs a few cents on gpt-oss-120b or Luna and about $0.46 on Sol.

## Use it for your own task

The method works for any task with an answer you can write down: write 20-30 items with the answer
you expect (include some borderline ones), run each several times, and count how often the model was
right, how often it gave the same answer every time, and where different models disagree. To adapt
the code, add a prompt to `PROMPTS` and a branch to `user_message()` in `run.py`, and write items
with a matching `task` field.

## Label audit

After reading the judges' reasons, three of my "clear" labels didn't hold up, so `analyse.py`
leaves them out of accuracy (`DISPUTED` in `common.py`):

- **s01**: my "complete" incident summary leaves out the 60% retry figure; 4, not 5.
- **s08**: my "complete" meeting summary widens a weekend-only rule to all search changes.
- **f06**: "webhook deliveries don't count at all" can be read as an overclaim.

On s07 (borderline) my label of 4 is out of line with my own marking guide, which makes it a 2.

## Limits

30 items is small: on 12 items, one mistake is about 8 points. The documents are short (about 250
words), each task used one prompt at low reasoning effort, and the labels are mine.
