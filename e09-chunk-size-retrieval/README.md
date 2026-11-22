# How much does chunk size change retrieval?

E09 cuts 60 public commercial contracts into chunks twelve ways and asks 334 plain questions about ten common clauses (governing law, renewal, liability cap and so on). It checks whether the complete clause, as marked by lawyers, reaches the model.

Status (22 Nov 2026): BM25 keyword search measured. Embedding runs (local MiniLM, OpenAI) pending. Not yet written up. Read DESIGN.md for the protocol and analysis/FULL-RESULTS.md for every number.

## First results, BM25, 1,000 words passed to the model

- Paragraph-aware chunks of up to 256 words found the complete clause for 254 of 334 questions, the most of any setting. Fixed 128-word chunks with 20% overlap found 246; the difference between those two is within noise (net +8, 95% interval −8 to +23 questions).
- Large chunks lost at a fixed budget: one 1,024-word chunk uses the whole budget, and found 172.
- Small chunks cut clauses before any search runs: at 64 words, 178 of 334 questions have no chunk holding a complete clause. For short facts this matters less: 64-word chunks still passed the governing state or country, from the clause itself, for 52 of 58 governing-law questions.

## E9b: reaching 90%

Methods were chosen on 20 contracts and scored once on the other 40 (223 questions). With BM25 at 1,000 words:

- Starting point (paragraph-aware 256): 173 of 223 (78%).
- Adding contract words to the question (a fixed list per clause type): 204 (91%, 95% interval 87–95%). At 2,000 words: 214 (96%).
- Section headers on chunks: 172 (no change). Small-to-big: 171 (no change).
- Whole contract: 100%, at a median of 7,706 words.

The word lists were written by hand, one per clause type. `pc_methods.py rewrite` tests the same idea with an LLM writing the words. Hybrid search, a re-ranker and Anthropic's contextual retrieval are also in `pc_methods.py`; see RUN-E9B.ps1. Results: analysis/IMPROVE-RESULTS.md.

## Run it

Python 3.10 or later. BM25 and the analysis use the standard library only.

```powershell
Set-Location 'E:\AI-ToolStack\Ai_toolstack_expirements\ai-toolstack-experiments\e09-chunk-size-retrieval'
python -m unittest -v test_e09
python retrieve_bm25.py
python analyse.py
```

Rebuild the data from CUAD (optional; data/ already holds the 60 contracts and 334 questions):

```powershell
git clone --depth 1 https://github.com/TheAtticusProject/cuad
Expand-Archive cuad\data.zip cuad-data
python build_items.py cuad-data\CUADv1.json
```

Embedding runs: see RUN-DENSE.ps1. The OpenAI run costs about $0.22 and needs OPENAI_API_KEY in a git-ignored `.env` in this folder.

## Files

- `data/contracts.jsonl`, `data/items.jsonl`: the 60 contracts and 334 questions with expert spans (from CUAD, CC BY 4.0).
- `chunking.py`, `bm25.py`, `scoring.py`, `keyfact.py`: chunkers, search, outcome labels, governing-law check.
- `retrieve_bm25.py`, `retrieve_dense.py`: write `results/<retriever>/rankings.jsonl`.
- `improve.py`, `pc_methods.py`: E9b methods; `improve.py` writes `analysis/IMPROVE-RESULTS.md` and `improve.json`.
- `analyse.py`: writes `analysis/FULL-RESULTS.md`, `boundaries.json`, `<retriever>.json`, `paired.json`, `examples.json`.

## Data credit

CUAD v1 by The Atticus Project (Hendrycks, Burns, Chen and Ball, 2021, "CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review"), licensed CC BY 4.0. The contract text and clause labels in `data/` are unchanged; the plain-English questions are ours.
