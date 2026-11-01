# E02 review before the full run

Status: pending Tej's review. The supplied brief says "Stop and wait for Tej's yes" after
the design and 10-item pilot. No full evaluation or approval record exists yet.

Read DESIGN.md and development/pilot-analysis/PILOT-REPORT.md, then inspect example.json
for what all four designs actually present on one shared failure schedule.

The choices needing review are:

- Is OSS-20B -> Sol the right historical response pair for this question?
- Are zero-numeric invoice defaults, a zero policy amount and a completed tool no-op useful
  synthetic failure behaviours? They are assumptions, not observed E06 defaults.
- Is the separate null-numeric invoice sensitivity sufficient?
- Are two retries versus one retry plus fallback/explicit failure reasonable limits?
- Are independent, persistent-primary and persistent-shared task episodes the right scope,
  with 1%, 5%, 20% rates and no claims about live queue congestion?
- Are the timing assumptions (429 0.2s, timeout 30s, fixed 1s/2s backoff) and cost-proxy
  bounds clear enough for the intended reader?
- Is the extra unverified outcome the honest treatment of silent tool no-ops?
- Are reused E06 cohorts and their template dependence acceptable, with no new synthetic tasks?

Expected evidence before approval: original E06 freeze verified; 102 items/1,428 responses
accounted for; E02 tests and freeze check pass; 3,680 pilot records replay exactly; no keys,
network calls, business-tool execution or held-out E02 outcome analysis occurred.

If changes are needed, record them in DESIGN.md before a new snapshot and pilot. Approval
must bind to the final reviewed snapshot. See README.md for the later offline commands.
