# Partial measured results, 8 November 2026

The free local model has completed 1,360 distinct embeddings, scoring for 360 pairs and 360 cache lookups, and 10,000 paired bootstrap resamples with a family sensitivity arm. The pre-run and post-run freeze checks pass. The API model has not run.

local.json, uncertainty.json and figures-data/ contain local results only. The combined report, model comparison and API opening-example selection remain pending. Do not treat this folder as a final publication handover.

The dataset has 30 near-miss families with six contextual variants each, ten paraphrase fact families and twenty distractor frames. The declared domain and template caps pass, but the contextual variants have correlated failure modes. Report these limits alongside any counts.

Run ../RUN-PAID.ps1 in PowerShell to embed the API model and regenerate the combined reports. After it completes, return results/local, results/api and analysis for claim verification and the final post handover. Provider credentials are read only by the API runner and remain outside these folders.

The model libraries and Ruff were installed into the active Python 3.10 environment during implementation. FREEZE.json records the model runtime versions. The local model was loaded at the recorded immutable weights revision on one CPU thread.
