# E09 measured results

Counts are questions (334 questions over 60 CUAD contracts). Retrieval searches only the chunks of the question's own contract.
Found = a retrieved chunk holds a complete expert-marked answer span. Intervals resample whole contracts.

## Answers cut by chunk boundaries (no model involved)

| Setting | Chunks | Questions with no complete answer in any chunk |
|---|---|---|
| fixed-64 | 10074 | 178 of 334 |
| fixed-64-ov20 | 12372 | 148 of 334 |
| fixed-128 | 5052 | 99 of 334 |
| fixed-128-ov20 | 6254 | 53 of 334 |
| fixed-256 | 2544 | 42 of 334 |
| fixed-256-ov20 | 3153 | 16 of 334 |
| fixed-512 | 1290 | 16 of 334 |
| fixed-512-ov20 | 1579 | 0 of 334 |
| fixed-1024 | 659 | 8 of 334 |
| fixed-1024-ov20 | 798 | 0 of 334 |
| para-256 | 3372 | 12 of 334 |
| para-512 | 1550 | 5 of 334 |

## bm25: same reading budget

The top-ranked chunks are passed until the next one would exceed the budget (at least one chunk).

| Setting | Budget (words) | Found | Partial | Missed | Cut | Found 95% CI | Median chunks |
|---|---|---|---|---|---|---|---|
| fixed-64 | 500 | 160 | 103 | 32 | 39 | 43%–53% | 7 |
| fixed-64 | 1000 | 214 | 85 | 17 | 18 | 59%–69% | 15 |
| fixed-64 | 2000 | 259 | 54 | 9 | 12 | 73%–82% | 31 |
| fixed-64-ov20 | 500 | 174 | 91 | 37 | 32 | 46%–58% | 7 |
| fixed-64-ov20 | 1000 | 210 | 79 | 23 | 22 | 57%–69% | 15 |
| fixed-64-ov20 | 2000 | 253 | 57 | 11 | 13 | 71%–81% | 31 |
| fixed-128 | 500 | 170 | 72 | 65 | 27 | 46%–56% | 3 |
| fixed-128 | 1000 | 223 | 60 | 37 | 14 | 61%–72% | 7 |
| fixed-128 | 2000 | 271 | 40 | 16 | 7 | 76%–86% | 15 |
| fixed-128-ov20 | 500 | 203 | 38 | 79 | 14 | 56%–65% | 3 |
| fixed-128-ov20 | 1000 | 246 | 31 | 51 | 6 | 69%–78% | 7 |
| fixed-128-ov20 | 2000 | 276 | 31 | 25 | 2 | 78%–87% | 15 |
| fixed-256 | 500 | 142 | 35 | 139 | 18 | 37%–48% | 1 |
| fixed-256 | 1000 | 229 | 27 | 70 | 8 | 64%–73% | 3 |
| fixed-256 | 2000 | 275 | 18 | 37 | 4 | 78%–86% | 7 |
| fixed-256-ov20 | 500 | 148 | 28 | 149 | 9 | 39%–50% | 1 |
| fixed-256-ov20 | 1000 | 221 | 24 | 83 | 6 | 62%–70% | 3 |
| fixed-256-ov20 | 2000 | 281 | 9 | 42 | 2 | 80%–88% | 7 |
| fixed-512 | 500 | 166 | 14 | 147 | 7 | 45%–55% | 1 |
| fixed-512 | 1000 | 170 | 14 | 143 | 7 | 46%–56% | 1 |
| fixed-512 | 2000 | 254 | 14 | 65 | 1 | 71%–81% | 3 |
| fixed-512-ov20 | 500 | 174 | 7 | 153 | 0 | 47%–58% | 1 |
| fixed-512-ov20 | 1000 | 178 | 7 | 149 | 0 | 48%–59% | 1 |
| fixed-512-ov20 | 2000 | 258 | 5 | 71 | 0 | 73%–82% | 3 |
| fixed-1024 | 500 | 172 | 7 | 152 | 3 | 46%–57% | 1 |
| fixed-1024 | 1000 | 172 | 7 | 152 | 3 | 46%–56% | 1 |
| fixed-1024 | 2000 | 184 | 7 | 140 | 3 | 50%–60% | 1 |
| fixed-1024-ov20 | 500 | 179 | 6 | 149 | 0 | 49%–59% | 1 |
| fixed-1024-ov20 | 1000 | 179 | 6 | 149 | 0 | 48%–58% | 1 |
| fixed-1024-ov20 | 2000 | 189 | 6 | 139 | 0 | 51%–63% | 1 |
| para-256 | 500 | 197 | 8 | 121 | 8 | 54%–64% | 2 |
| para-256 | 1000 | 254 | 9 | 68 | 3 | 72%–80% | 4 |
| para-256 | 2000 | 291 | 8 | 34 | 1 | 83%–91% | 9 |
| para-512 | 500 | 174 | 2 | 155 | 3 | 47%–58% | 1 |
| para-512 | 1000 | 219 | 2 | 110 | 3 | 60%–72% | 2 |
| para-512 | 2000 | 280 | 2 | 49 | 3 | 80%–88% | 4 |

## bm25: complete answers by clause type at 1,000 words

| Clause | Questions | fixed-64 | fixed-64-ov20 | fixed-128 | fixed-128-ov20 | fixed-256 | fixed-256-ov20 | fixed-512 | fixed-512-ov20 | fixed-1024 | fixed-1024-ov20 | para-256 | para-512 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Anti-Assignment | 53 | 48 | 48 | 47 | 50 | 45 | 48 | 36 | 40 | 38 | 37 | 50 | 47 |
| Audit Rights | 34 | 23 | 20 | 22 | 26 | 26 | 28 | 20 | 18 | 23 | 23 | 27 | 27 |
| Cap On Liability | 41 | 21 | 20 | 25 | 23 | 30 | 24 | 23 | 21 | 26 | 26 | 30 | 25 |
| Change Of Control | 16 | 9 | 11 | 11 | 13 | 12 | 13 | 11 | 10 | 12 | 12 | 14 | 12 |
| Expiration Date | 55 | 38 | 37 | 39 | 42 | 32 | 30 | 21 | 25 | 20 | 23 | 39 | 27 |
| Governing Law | 60 | 45 | 42 | 40 | 46 | 44 | 44 | 36 | 34 | 28 | 31 | 47 | 39 |
| Non-Compete | 14 | 1 | 2 | 2 | 3 | 4 | 3 | 3 | 4 | 4 | 5 | 4 | 4 |
| Notice Period To Terminate Renewal | 15 | 4 | 4 | 8 | 9 | 5 | 2 | 3 | 3 | 2 | 3 | 7 | 5 |
| Renewal Term | 27 | 11 | 10 | 15 | 17 | 19 | 17 | 11 | 13 | 10 | 11 | 19 | 19 |
| Termination For Convenience | 19 | 14 | 16 | 14 | 17 | 12 | 12 | 6 | 10 | 9 | 8 | 17 | 14 |

## bm25: Governing Law, is the place named in what the model receives?

| Setting | Budget | Questions | Jurisdiction named | Complete span |
|---|---|---|---|---|
| fixed-64 | 500 | 58 | 40 | 30 |
| fixed-64 | 1000 | 58 | 52 | 45 |
| fixed-64 | 2000 | 58 | 55 | 52 |
| fixed-64-ov20 | 500 | 58 | 41 | 35 |
| fixed-64-ov20 | 1000 | 58 | 49 | 42 |
| fixed-64-ov20 | 2000 | 58 | 55 | 50 |
| fixed-128 | 500 | 58 | 37 | 33 |
| fixed-128 | 1000 | 58 | 47 | 39 |
| fixed-128 | 2000 | 58 | 56 | 50 |
| fixed-128-ov20 | 500 | 58 | 39 | 35 |
| fixed-128-ov20 | 1000 | 58 | 48 | 45 |
| fixed-128-ov20 | 2000 | 58 | 53 | 50 |
| fixed-256 | 500 | 58 | 30 | 28 |
| fixed-256 | 1000 | 58 | 45 | 43 |
| fixed-256 | 2000 | 58 | 54 | 52 |
| fixed-256-ov20 | 500 | 58 | 26 | 26 |
| fixed-256-ov20 | 1000 | 58 | 45 | 43 |
| fixed-256-ov20 | 2000 | 58 | 54 | 53 |
| fixed-512 | 500 | 58 | 35 | 34 |
| fixed-512 | 1000 | 58 | 37 | 36 |
| fixed-512 | 2000 | 58 | 47 | 45 |
| fixed-512-ov20 | 500 | 58 | 32 | 32 |
| fixed-512-ov20 | 1000 | 58 | 33 | 33 |
| fixed-512-ov20 | 2000 | 58 | 49 | 48 |
| fixed-1024 | 500 | 58 | 29 | 28 |
| fixed-1024 | 1000 | 58 | 29 | 28 |
| fixed-1024 | 2000 | 58 | 34 | 33 |
| fixed-1024-ov20 | 500 | 58 | 30 | 30 |
| fixed-1024-ov20 | 1000 | 58 | 30 | 30 |
| fixed-1024-ov20 | 2000 | 58 | 35 | 35 |
| para-256 | 500 | 58 | 39 | 40 |
| para-256 | 1000 | 58 | 46 | 46 |
| para-256 | 2000 | 58 | 54 | 54 |
| para-512 | 500 | 58 | 31 | 31 |
| para-512 | 1000 | 58 | 38 | 38 |
| para-512 | 2000 | 58 | 50 | 50 |

## bm25: top k

| Setting | k | Found | Partial | Missed | Cut | Found 95% CI | Median words to model |
|---|---|---|---|---|---|---|---|
| fixed-64 | 1 | 53 | 101 | 80 | 100 | 12%–20% | 64 |
| fixed-64 | 3 | 106 | 115 | 53 | 60 | 27%–37% | 192 |
| fixed-64 | 5 | 143 | 111 | 36 | 44 | 38%–47% | 320 |
| fixed-64-ov20 | 1 | 62 | 89 | 98 | 85 | 15%–23% | 64 |
| fixed-64-ov20 | 3 | 133 | 92 | 56 | 53 | 35%–45% | 192 |
| fixed-64-ov20 | 5 | 155 | 94 | 45 | 40 | 40%–52% | 320 |
| fixed-128 | 1 | 101 | 66 | 115 | 52 | 26%–35% | 128 |
| fixed-128 | 3 | 170 | 71 | 65 | 28 | 46%–56% | 384 |
| fixed-128 | 5 | 200 | 68 | 45 | 21 | 54%–66% | 640 |
| fixed-128-ov20 | 1 | 109 | 54 | 145 | 26 | 27%–38% | 128 |
| fixed-128-ov20 | 3 | 201 | 37 | 81 | 15 | 56%–65% | 384 |
| fixed-128-ov20 | 5 | 231 | 34 | 61 | 8 | 65%–74% | 640 |
| fixed-256 | 1 | 139 | 35 | 142 | 18 | 37%–46% | 256 |
| fixed-256 | 3 | 227 | 28 | 71 | 8 | 63%–73% | 768 |
| fixed-256 | 5 | 253 | 26 | 50 | 5 | 71%–80% | 1280 |
| fixed-256-ov20 | 1 | 146 | 28 | 151 | 9 | 39%–49% | 256 |
| fixed-256-ov20 | 3 | 220 | 25 | 83 | 6 | 62%–70% | 768 |
| fixed-256-ov20 | 5 | 256 | 19 | 57 | 2 | 72%–81% | 1280 |
| fixed-512 | 1 | 166 | 14 | 147 | 7 | 45%–55% | 512 |
| fixed-512 | 3 | 250 | 15 | 68 | 1 | 71%–79% | 1536 |
| fixed-512 | 5 | 287 | 8 | 38 | 1 | 82%–89% | 2560 |
| fixed-512-ov20 | 1 | 174 | 7 | 153 | 0 | 47%–57% | 512 |
| fixed-512-ov20 | 3 | 254 | 5 | 75 | 0 | 71%–81% | 1536 |
| fixed-512-ov20 | 5 | 282 | 5 | 47 | 0 | 80%–88% | 2560 |
| fixed-1024 | 1 | 172 | 7 | 152 | 3 | 47%–56% | 1024 |
| fixed-1024 | 3 | 280 | 4 | 50 | 0 | 79%–88% | 3072 |
| fixed-1024 | 5 | 313 | 1 | 20 | 0 | 91%–96% | 5093 |
| fixed-1024-ov20 | 1 | 179 | 6 | 149 | 0 | 49%–59% | 1024 |
| fixed-1024-ov20 | 3 | 272 | 5 | 57 | 0 | 77%–86% | 3072 |
| fixed-1024-ov20 | 5 | 304 | 6 | 24 | 0 | 88%–94% | 5120 |
| para-256 | 1 | 169 | 7 | 150 | 8 | 46%–56% | 236 |
| para-256 | 3 | 236 | 5 | 87 | 6 | 66%–75% | 682 |
| para-256 | 5 | 265 | 9 | 57 | 3 | 75%–83% | 1120 |
| para-512 | 1 | 174 | 2 | 155 | 3 | 47%–57% | 474 |
| para-512 | 3 | 257 | 2 | 72 | 3 | 72%–81% | 1378 |
| para-512 | 5 | 291 | 4 | 38 | 1 | 83%–91% | 2279 |

## bm25: paragraph-aware 256 against each setting at 1,000 words, question by question

| Other setting | Only para-256 found | Only other found | Net | Net 95% CI (contracts resampled) |
|---|---|---|---|---|
| fixed-64 | 62 | 22 | +40 | +21 to +59 |
| fixed-64-ov20 | 66 | 22 | +44 | +22 to +65 |
| fixed-128 | 53 | 22 | +31 | +13 to +49 |
| fixed-128-ov20 | 29 | 21 | +8 | -8 to +23 |
| fixed-256 | 40 | 15 | +25 | +12 to +38 |
| fixed-256-ov20 | 43 | 10 | +33 | +19 to +47 |
| fixed-512 | 99 | 15 | +84 | +65 to +102 |
| fixed-512-ov20 | 88 | 12 | +76 | +58 to +95 |
| fixed-1024 | 99 | 17 | +82 | +62 to +101 |
| fixed-1024-ov20 | 92 | 17 | +75 | +55 to +95 |
| para-512 | 51 | 16 | +35 | +20 to +51 |

## Limits

- One public contract set (CUAD, US commercial contracts filed with the SEC). Ten clause types, with fixed plain-English questions.
- An expert span marks where a lawyer looked, not the only text that could answer the question; a chunk can be useful without holding the whole span.
- Questions inside one contract are correlated, so intervals resample contracts, not questions.
- BM25 is keyword search. Embedding results come from separate runs on the author's PC.
