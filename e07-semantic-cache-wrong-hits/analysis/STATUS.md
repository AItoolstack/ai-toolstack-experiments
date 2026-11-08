# Measured runs completed, 8 November 2026

Both models have completed 1,360 distinct embeddings each. Scoring covers 360 pairs and 360 cache lookups per model. The combined analysis contains 10,000 paired item-bootstrap resamples, paired model differences and a family sensitivity arm. The final freeze check passes. The API run recorded no request failures.

Neither model meets the observed near-miss error budget at any tested threshold. The generated results, chart data and opening-example selection now include the API run. The post still needs editorial claim verification before publication.

The dataset has 30 near-miss families with six contextual variants each, ten paraphrase fact families and twenty distractor frames. Contextual variants have correlated failure modes. These results describe this synthetic set and its constructed cache traffic mix.

The model libraries and Ruff were installed into the active Python 3.10 environment during implementation. FREEZE.json records exact model runtime versions. The local model used the recorded immutable weights revision on one CPU thread. API request timings include network and provider latency.
