# E9b: getting the complete clause to the model

Starting point: paragraph-aware chunks up to 256 words, BM25. Methods were chosen on 111 dev questions (20 contracts).
Headline numbers are on 223 test questions (40 contracts) that were not used to choose anything.
Found = the text passed to the model covers a complete expert-marked clause. Intervals resample contracts.

## Test contracts (headline)

| Method | Budget (words) | Found | Rate | 95% CI | Median words passed |
|---|---|---|---|---|---|
| baseline | 1000 | 173 of 223 | 78% | 73%–82% | 902 |
| baseline | 2000 | 195 of 223 | 87% | 82%–92% | 1,890 |
| headers | 1000 | 172 of 223 | 77% | 73%–82% | 884 |
| headers | 2000 | 193 of 223 | 87% | 81%–91% | 1,858 |
| expansion | 1000 | 204 of 223 | 91% | 87%–95% | 896 |
| expansion | 2000 | 214 of 223 | 96% | 94%–98% | 1,885 |
| small-to-big | 1000 | 171 of 223 | 77% | 73%–81% | 916 |
| small-to-big | 2000 | 189 of 223 | 85% | 80%–89% | 1,883 |
| headers+expansion | 1000 | 204 of 223 | 91% | 87%–95% | 885 |
| headers+expansion | 2000 | 214 of 223 | 96% | 93%–98% | 1,854 |
| small-to-big+expansion | 1000 | 205 of 223 | 92% | 89%–95% | 893 |
| small-to-big+expansion | 2000 | 210 of 223 | 94% | 91%–97% | 1,889 |
| whole contract | 1000 | 223 of 223 | 100% | 100%–100% | 7,706 |
| whole contract | 2000 | 223 of 223 | 100% | 100%–100% | 7,706 |

## Dev contracts (used to choose)

| Method | Budget (words) | Found | Rate | 95% CI | Median words passed |
|---|---|---|---|---|---|
| baseline | 1000 | 81 of 111 | 73% | 65%–81% | 892 |
| baseline | 2000 | 96 of 111 | 86% | 79%–93% | 1,900 |
| headers | 1000 | 81 of 111 | 73% | 65%–81% | 886 |
| headers | 2000 | 95 of 111 | 86% | 78%–92% | 1,860 |
| expansion | 1000 | 104 of 111 | 94% | 88%–98% | 892 |
| expansion | 2000 | 107 of 111 | 96% | 91%–100% | 1,912 |
| small-to-big | 1000 | 77 of 111 | 69% | 60%–79% | 901 |
| small-to-big | 2000 | 90 of 111 | 81% | 73%–89% | 1,901 |
| headers+expansion | 1000 | 104 of 111 | 94% | 88%–98% | 881 |
| headers+expansion | 2000 | 107 of 111 | 96% | 91%–100% | 1,839 |
| small-to-big+expansion | 1000 | 103 of 111 | 93% | 86%–98% | 908 |
| small-to-big+expansion | 2000 | 106 of 111 | 96% | 90%–99% | 1,904 |
| whole contract | 1000 | 111 of 111 | 100% | 100%–100% | 6,614 |
| whole contract | 2000 | 111 of 111 | 100% | 100%–100% | 6,614 |

## Notes

- Whole contract: always contains the clause, by definition; the cost is the median words passed.
- Headers: the nearest section heading is added to each chunk before search and counted in the budget.
- Expansion: a fixed list of contract words per clause type, written before the run.
- Small-to-big: search 64-word pieces (overlap 12), pass the paragraph-aware chunk each one sits in.
- Rewrite (an LLM writes the search words), hybrid, rerank and contextual appear only after the PC runs (results/<method>/rankings.jsonl). Contextual is run on the test contracts only.
