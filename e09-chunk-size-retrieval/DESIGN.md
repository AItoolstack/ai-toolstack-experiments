# E09 design: how much does chunk size change retrieval?

Status: built and first run on 22 Nov 2026 (BM25 keyword search). Embedding runs pending on the author's PC. Not yet reviewed by Tej.

## Question

Before a RAG system can answer a question about a long document, it cuts the document into chunks and retrieves a few. Does the answer survive the cut, and does the search find it? Which chunking settings get the complete answer to the model within a fixed reading budget?

## Data

- CUAD v1 (The Atticus Project; Hendrycks, Burns, Chen and Ball, 2021), CC BY 4.0. 510 US commercial contracts filed with the SEC, with clauses marked by lawyers for 41 categories. Source: github.com/TheAtticusProject/cuad, data.zip sha256 f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a (repo commit 67faa0e).
- Contracts of at least 3,000 words, 60 drawn with seed 9009 (median 6,990 words, 3,094 to 45,650). Stored in data/contracts.jsonl.
- Ten clause types, each with one fixed plain-English question (common.py). A question is asked of a contract only when the lawyers marked that clause in it: 334 questions (data/items.jsonl). The gold answer is the set of expert-marked spans; any one complete span counts.
- Shortest gold span per question: median 31 words, 90th percentile 73, longest 218.

## Chunking settings (12)

- Fixed windows of 64, 128, 256, 512 and 1,024 words, with no overlap and with 20% overlap.
- Paragraph-aware at 256 and 512 words: whole blank-line paragraphs merged up to the limit; a paragraph longer than the limit is split into fixed windows. Median paragraph: 48 words.
- Sizes are in words. One English word is roughly 1.3 tokens.

## Retrieval

- Search is within the question's own contract (asking a question about one document), not across all 60.
- BM25 (k1 1.5, b 0.75, lowercase alphanumeric tokens), standard library, run in the cloud workspace.
- Embeddings, run on the author's PC: all-MiniLM-L6-v2 (local; reads at most 256 word pieces, about 190 words, so longer chunks are truncated) and OpenAI text-embedding-3-small (about $0.22 for every chunk of every setting). Cosine similarity.

## Measures

- **Boundary count (no model):** questions where no single chunk holds a complete answer span.
- **Reading budget (main comparison):** pass top-ranked chunks until the next would exceed 500, 1,000 or 2,000 words (always at least one chunk, so a 1,024-word chunk exceeds the 500 and 1,000 budgets).
- **Top k:** k = 1, 3, 5, with the median words passed.
- **Outcome per question:** found (the passed chunks together cover a complete answer span), partial (they touch an answer but miss part of it), missed (nothing passed touches an answer although a complete one existed in some chunk), cut (nothing passed touches an answer and no chunk held a complete one).
- **Governing Law key fact:** does a passed chunk contain the place name as written inside the clause (not an address elsewhere)? Checks whether the strict span rule overstates harm for short facts. 58 of 60 clauses name a place.
- **Uncertainty:** questions within one contract are correlated, so 95% intervals resample whole contracts (2,000 resamples). Paired comparisons count questions found by only one of two settings.

## Changes during the run (22 Nov 2026, recorded before any embedding run)

1. Added the reading-budget comparison after the first top-k table: top-k rewards big chunks because k big chunks pass far more words.
2. Added the Governing Law key-fact check after reading cut examples where the half passed still named the state.
3. Changed "found" from "one passed chunk holds a complete span" to "the passed chunks together cover a complete span". Three of the first nine cut examples had both halves retrieved, so the model did receive the whole clause, in two pieces. The boundary count still uses the single-chunk rule. Under the old rule, fixed-64 at 1,000 words found 123 answers; under the new rule, 214. Paragraph-aware 256 stayed highest under both (250 and 254).

## Limits

- One document type: US commercial contracts, clean text from SEC filings, many with blank-line paragraphs. PDFs without that structure would not benefit from paragraph-aware chunking in the same way.
- Ten clause types, one fixed question each. Real users phrase questions differently.
- An expert span marks where a lawyer looked, not the only text that could answer the question.
- Retrieval within one contract. Searching across many documents adds a different failure (the wrong contract).
- No model answers questions here: this measures what reaches the model, not what it says.

# E9b: can common methods get the complete clause to the model for 90% of questions?

Added 22 Nov 2026 at Tej's request, after E9's first run.

## Fair split
The 60 contracts are split with seed 9010 into 20 dev contracts (111 questions) and 40 test contracts (223 questions). Methods and their settings were chosen on dev only. The test contracts were scored once, after the methods were fixed. Lists are in analysis/improve.json.

## Starting point
Paragraph-aware chunks up to 256 words with BM25 (E9's best), budgets of 1,000 and 2,000 words.

## Methods
Run in the cloud workspace (BM25):
- Expansion: a fixed list of contract words added to each question, one list per clause type (improve.py). Written from general contract wording before the E9b run. Caveat: written after reading E9's cut examples, and each clause type has one fixed question, so a list per type is a strong advantage; real users' questions vary. The LLM rewrite method below removes the human list.
- Headers: the nearest numbered section heading (with its parent section) added to each chunk before search, and counted in the budget.
- Small-to-big: search 64-word pieces (12-word overlap), pass the 256-word paragraph-aware chunk each piece sits in.
- Combinations of the above, and the whole contract (always contains the clause; the cost is its length).

Run on Tej's PC (pc_methods.py, one at a time):
- Rewrite: an LLM writes 6 to 12 search words for each of the 10 questions (10 calls); BM25 searches with question + words.
- Hybrid: BM25 and embeddings (E9's local or OpenAI run) merged by reciprocal rank fusion (k = 60).
- Rerank: BM25's top 30 re-scored by cross-encoder/ms-marco-MiniLM-L-6-v2 (local, free).
- Contextual: Anthropic's contextual retrieval prompt; an LLM writes a short context for each chunk given the whole contract; BM25 over context + chunk. Test contracts only (2,096 chunks; about 50M input tokens before caching).

## Changes during E9b (dev only)
- The first heading detector found one heading in a 20-section contract. Rewritten on dev contracts to catch inline numbered headings ("13.2 Governing Law. This Agreement...") and keep the parent section. Headers still did not change BM25 results on dev (most headings already sit inside the chunk text). Kept as tested, not dropped.

## First E9b results (test contracts, BM25, 1,000 words)
Baseline 173 of 223 (78%, 73–82%). Expansion 204 (91%, 87–95%). Headers 172. Small-to-big 171. Small-to-big + expansion 205 (92%). At 2,000 words, expansion 214 (96%). Whole contract 223 (100%), median 7,706 words.
