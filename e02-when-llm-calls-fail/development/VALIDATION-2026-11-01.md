# Review milestone validation: 1 November 2026

Status: ready for Tej's design/pilot review, not an approved full evaluation.

Checked with Python 3.10.10 on Windows/PowerShell:

- `run-pilot.ps1` passed end to end: E06 input freeze, E02 review snapshot, 19 unit tests,
  resumable 10-item pilot, complete ledger replay/scoring, diagnostic fixtures, final freeze.
- All 102 existing synthetic items and 1,428 historical response records are accounted for.
- The current pilot has 46 complete shards and 3,680 records. It contains ten development
  items, one fixed seed and one primary track; both default variants remain separate.
- The seed triggered zero initial injected failures up to 20%. Its original snapshot and
  pilot are preserved under initial-pilot, with original sources in commit c095dcb.
- Current summary.json and uncertainty.json equal the archived original values exactly.
  No seed, failure rate, recovery limit, task or key was changed to create a result.
- The 600 separately labelled scripted diagnostics exercise all five failure types on
  the same ten development items. Their gzip ledger round-trips exactly. They never enter
  the probabilistic summaries or confidence calculations.
- Independently checked all 1,472 scenario/variant/task/design summary groups: outcomes
  sum to their denominators, and paired point differences match both comparison policies.
- Ruff checks and Python compilation passed. Git whitespace checks passed.
- The flow diagram was rendered with Matplotlib 3.10.9 and the existing E06 Inter font,
  checked visually for clipping/overlap, and verified as 960 x 1344 PNG (480px display).
  Its SVG, caption, metadata and generator are included. No results chart was generated.
- An actual `run.py --full --cohort heldout` invocation failed at the missing-approval
  gate before creating a results directory. APPROVAL.json does not exist.

The primary-pair E02 held-out outcomes have not been analysed. Loading the existing corpus
for input coverage/health is not a new held-out policy evaluation. No API calls or business
tool executions occurred, and no credentials were needed or read. Model-usage spend: $0.

The optional figure environment is local and ignored by Git. The committed harness uses
only the Python standard library; Matplotlib is needed only for figure generation.
No files in E06 or other experiment folders were changed. No push or publication occurred.
