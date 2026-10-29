# Frozen-configuration preflight review: 29 October 2026

**Outcome: proceed to evaluation.** Inspected all 18 saved compatibility responses under
`results_frozen_20261029_preflight/`. The local `e06-frozen` tag remains at `ffaf7e3` and
`freeze.py --check` passes. No frozen source, item, key, prompt or setting was changed.

- All six models have exactly `inv01`, `tl01`, `rl01`, repeat zero, marked preflight.
- Frozen request-set hashes, saved configuration fingerprints and model IDs all match.
- Hosts are Groq for both OSS models, Z.AI for both GLM arms, OpenAI for Luna/Sol.
- All six tool responses contain one native tool call with valid argument schema.
- Invoice fields and rules amounts parse and pass the existing non-gold validators.
- No incomplete response, cutoff, recorded retry or separate error log was found.
- Input, output and reasoning-token fields are present. Maximum output is 202 tokens;
  this does not establish how the host would enforce the cap on a longer response.

Both GLM invoice responses use code fences. The existing parser accepts them, as already
documented; this is not strict JSON-only compliance. No prompt or parser tuning is needed.
Temperature zero was accepted but determinism and internal host compliance remain unproven.

The successful-call list-price estimate for these probes is $0.006325775, not billing
reconciliation. Machine-readable checks and raw-file hashes are saved in
`analysis_frozen_20261029_preflight/preflight-health-2026-10-29.json`.

Tej can now run, from the experiment folder:

```powershell
.\run-full.ps1 -Stage evaluation
```

This makes up to 1,428 paid calls: 306 per cheap candidate and 102 each for Sol and the
control. Pilot-based projection remains approximately $0.33, or $0.47 at double output.
The script checks the freeze and stops on model-process failure. Repeating the same command
resumes compatible saved rows. Preflight responses stay outside evaluation scoring.

After completion, inspect run health and selected answers before computing accuracy.
Report 81 held-out items separately from the 21 development items. The assistant made no
paid calls or credential reads during this review.
