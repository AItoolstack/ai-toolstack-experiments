# When does a semantic cache serve the answer to a different question?

Design for Tej's review, 8 November 2026. No model scores have been seen. The first milestone uses only 30 synthetic near-misses and an offline dry run. Tej reviews this milestone before the full set is written.

## What would change our minds?

Measure whether the model retrieves a stored answer that still answers the incoming question. We expect short edits to entities or direction to sometimes pass a high similarity threshold. It would surprise us if a model met the error budget and kept most paraphrases, even before a guard. That would support using a threshold alone on this workload. Conversely, a threshold that rejects every question offers no reuse. Report the useful count at the selected threshold. The experiment specifies no universal minimum level of useful reuse.

## Items and answer key

Plan 360 distinct pairs: 120 paraphrases, 180 near-misses (30 each for entity/ID, negation, number/date, scope/qualifier, direction/word order and actor/permission), and 60 unrelated pairs on the same topic. The 30 review items count towards the 180 if retained after audit. All material is newly authored and synthetic under the repository licence. Support and policy answers describe fictional fixtures. No public corpus is used.

Embed only the two question texts. Keep the stored answer, the answer the query requires, and a short reason for the label with the key. A changed ID alone is insufficient if the same answer would work. Mix short edits with reworded requests, plain questions with instructions, and short with longer contexts. Include close and distant paraphrases in the full set. Never select or discard items using their similarity scores.

Within each of the eight groups (six near-miss types, paraphrases and unrelated pairs), use at least four domains, at most 35% from one domain and at most 25% from one wording template. In a five-item review group, these caps require five distinct domains and five distinct template families. Travel joins shop support, insurance, IT helpdesk and general knowledge. Template means the same phrasing frame with slot substitutions. Keep the same family name across such substitutions. The builder checks declared families and repeated numeric-slot frames. Human review checks paraphrased templates and the domain assignments.

## Audit and freeze

After design approval, draw 72 items with seed 7007: 12 paraphrases, 12 unrelated and eight per near-miss type. Shuffle their order, randomly swap question order and use opaque audit IDs. Give a separate reviewer only the two texts and the instruction to mark same question, different question, or ambiguous with a reason. Withhold answers, labels, type, filenames encoding labels and model output. Log the original judgement, disagreements, changes and reasons here. Re-audit rewritten examples blind before freezing them. Check that alternate acceptable stored answers in the cache have been enumerated. If the fixture cannot resolve an ambiguity, replace the item before freezing.

Before any real-model run, freeze the final item and cache manifests, acceptable IDs, model identities and dimensions, dependency versions, source hashes, protocol, metrics and example rule in FREEZE.json. Run freeze.py --check before embedding and again after the run. Record subsequent decisions in a dated exploratory file. This review draft has no frozen dataset yet.

## Pair scores and cache lookups

Compute cosine similarity on unrounded vectors. Serve at similarity >= threshold. Sweep integer hundredths from 80 to 99 inclusive, independently for each model. For each threshold count paraphrase hits out of 120, near-miss wrong hits out of 180, unrelated wrong hits out of 60, and near-miss wrong hits of each type out of 30. The safe threshold is the lowest tested value with at most two wrong hits out of 180 unguarded near-miss pairs. Report useful hits there, or report that none qualifies. Two in 180 is an observed count on this set. It cannot establish a population error ceiling. Report both models' thresholds, including their difference when both exist.

Build one static cache of 1,000 distinct stored questions: one source per pair and 640 independently authored distractors. No test query text may also occur in the cache. Before retrieval, assign each query the complete set of acceptable stored IDs for its intended answer, including equivalent alternatives. An empty set means any served answer is wrong. Review the key against the full cache, including distractors. Return the nearest entry across all 1,000; break exact ties by smallest stored ID. Apply the threshold to that entry and score its ID against the query's key. Record query ID, winning ID, cosine, eligibility and outcome. Score one lookup per distinct query. At each threshold count useful serves, wrong serves and abstentions out of 360 lookups and by origin group with its own lookup denominator. Show served counts alongside them. A near-miss query can legitimately retrieve a different, correct entry.

## Guard, uncertainty and selection

Apply the guard after selecting the top entry (or to the specified source for a pair). A mismatch abstains; no second candidate is tried. Compare multisets of numeric literals, digit-bearing identifiers, supported dates and negation markers. Lowercase and normalise curly apostrophes. Keep literal spellings, duplicates and leading zeros. Recognise signed integers, decimals, ISO and slash dates, and day–English month–optional year; freeze exact regex and supported formats before the run. Negation list: no, not, never, neither, nor, without, cannot, and words ending in n't. Number words and unlisted paraphrases can slip through. Keeping the same numbers in reverse order can pass. Compare guarded and unguarded counts at every threshold, especially each model's own unguarded safe threshold. Count wrong hits removed and useful hits lost by group. If no safe threshold exists, label the safe-threshold figure data unavailable.

Use 10,000 paired item-bootstrap resamples, seed 7007. Sample with replacement within each of the eight groups and carry the same item indices across models, arms, thresholds and cache lookups. Use 2.5th and 97.5th percentiles for counts and paired differences at each fixed threshold. Intervals at a selected threshold are descriptive and conditional on that threshold. A bootstrap stratum with zero observed errors has no information about unseen errors. Avoid ranking heavily overlapping estimates.

For the opening example select the incorrectly served near-miss pair with highest API cosine anywhere on the unguarded sweep, ties by ascending item ID. Name the threshold it passed. If none passes any tested threshold, lead with the useful count and zero observed near-miss hits. Do not present a closest rejected pair as a served answer.

## Models, cost and timing

Use sentence-transformers/all-MiniLM-L6-v2 (384 dimensions; raw question text, default sentence embedding) and OpenAI text-embedding-3-small (default 1,536 dimensions). Pin the local weights revision and installed software versions at freeze. Record the requested and returned API identifiers and UTC run dates; the hosted alias may have no immutable weights revision. [Local model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) · [API embedding guide](https://developers.openai.com/api/docs/guides/embeddings)

Illustrative budget: 1,360 unique texts × 100 assumed input tokens × $0.02 per million = $0.00272 for one pass. Recalculate from the frozen input, current price and retry allowance before giving Tej the PowerShell command. Tej runs any paid command; an estimate over $2 requires his review first. [API model pricing](https://developers.openai.com/api/docs/models/text-embedding-3-small)

Embed cache entries separately from incoming queries. Measure each uncached query singly with a monotonic clock, from encoding/request start until its vector is available. Record milliseconds, equipment, model revision, request count, retries and failures. Exclude model loading, retries and disk-cache reads from the single-attempt latency summary; report those counts separately. Give median and 95th percentile with denominator. Cache each completed embedding by exact text, model, revision and settings. Resume without issuing calls for completed inputs.

## Handover

FULL-RESULTS.md and RESULTS.md will trace each claim to a file and field. Supply figure data for the threshold sweep, wrong hits by type and guard before/after. Use pair counts with denominators in pair charts and lookup counts with denominators in simulation charts. HANDOVER-FOR-POST.md will give the opening example, three or four evidenced claims and limits. Production traffic mix, savings from avoided calls, and population safety are outside this experiment.

## Changes after review

8 November 2026. Before measurements, set the local CPU encoder to one PyTorch thread and record that setting in the model identity. This makes the latency setup explicit. The API timing includes network and provider latency.

8 November 2026. Tej approved proceeding after the 30-item milestone. Before any model measurements, expanded the candidate corpus to 360 pairs and completed the separate blind audit. All 72 judgements agree with the hidden key. See development/AUDIT.md and the original responses.

8 November 2026. Corpus construction choices recorded before measurements. The 180 near-misses contain 30 question families, with the original and five contextual variants per family. The 120 paraphrases use ten fact families, two paraphrase distances and six contexts. The 60 unrelated pairs use those same ten topics with a different requested fact. Domain and declared template caps pass, but the variants are correlated and the phrasing diversity is limited. Add a family bootstrap sensitivity analysis alongside the required paired item bootstrap. It samples families within each group and carries the weights across models and arms.

8 November 2026. Cache amendment before measurements. Several sources recur across the paraphrase and unrelated pairs. Deduplicate identical questions with identical answers, leaving 240 distinct sources. Add 760 generated distractors from twenty question frames across the five domains to reach 1,000 distinct stored questions. This supersedes the planned 640 independently authored distractors. Report the construction as a limitation. The acceptable-answer key is based on exact equality of the authored required answer text with each stored answer. This includes equivalent entries across contextual variants; complete semantic equivalence remains subject to review.

8 November 2026. Runner uses single attempts and stops on request failure. Failures are recorded by input hash without provider response bodies. Resumption retries only missing embeddings. Exclude queries that previously failed from the single-attempt latency summary and report their count. The estimated budget uses total UTF-8 input bytes as a conservative token bound at the assumed current price, including a two-pass allowance.
