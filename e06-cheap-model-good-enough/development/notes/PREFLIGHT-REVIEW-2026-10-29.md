# Six-model preflight review: 29 October 2026

**Outcome: proceed to the pilot.** Tej ran all 18 compatibility calls successfully. All
18 saved responses have been inspected. This is a transport/format review, not an accuracy
evaluation, and the probes remain separate from scored pilot data.

Source: `results_samples_sixmodel_20261029_preflight/`.
Machine-readable checks and source hashes:
`analysis_samples_sixmodel_20261029_preflight/preflight-health-2026-10-29.json`.

- All six models have exactly `inv01`, `tl01` and `rl01`, at repeat zero, marked preflight.
- All saved model IDs and request fingerprints match the current configuration.
- Both OSS models report Groq; both GLM arms report Z.AI; Luna and Sol report OpenAI.
- All six tool probes return one native tool call with valid argument shape and schema.
  No business tool is executed by this experiment.
- Invoice fields and rules amounts parse through the existing parser. The existing v2
  validators pass for all probes without consulting gold answers.
- No cutoff, incomplete response, recorded retry or separate error log was found.
- Input, output and reasoning-token counts are present for every response. Zero reasoning
  tokens is a reported value. The largest output is 199 tokens, below the configured 2,000.
  This does not prove enforcement of the limit on a long response.

## Format caveat retained

GLM's default-temperature `inv01` wraps its JSON in a Markdown code fence. The existing
parser accepts this, as it already does for historical runs. It is not strict JSON-only
compliance. Preserve the response and parser; do not change one model's prompt to tune it.
All other invoice/rules probe bodies are strict JSON.

The temperature-zero request was accepted, but these probes cannot establish determinism or
that the host honoured temperature internally. That remains a limitation, not a passed test.

## Cost and next step

Reported successful-call tokens and configured list prices imply **$0.006318175** for the
18 preflight calls. Extrapolating these three simple items per model to seven per task gives
approximately **$0.04423** for the upcoming 126-call pilot. That is a coarse planning estimate;
harder items may use more output. Recalculate the full-study budget from the completed pilot.
These estimates do not reconcile billing or include earlier development runs.

Tej's next command, from this experiment folder:

```powershell
.\run-pilot.ps1 -Stage pilot
```

This makes up to 126 paid calls, saved under `results_samples_sixmodel_20261029/`. After Tej
completes it, review run health and three answers per model per task before accuracy. No
pilot or other paid calls were initiated by the reviewing assistant.
