# E02: completed results

**Current status: approved offline evaluation complete, 1 November 2026. Ready for review and Git push.**

Start with [FULL-RESULTS.md](FULL-RESULTS.md), [RESULTS.md](RESULTS.md), and
[HANDOVER-FOR-POST.md](HANDOVER-FOR-POST.md). The approved protocol is [DESIGN.md](DESIGN.md).

The original README.md, DESIGN.md and REVIEW-CHECKLIST.md are retained byte-for-byte as historical
parts of the approved snapshot. Their pre-run status statements describe the moment of that snapshot.
APPROVAL.json and this results entry point record the subsequent approval and completion.

Verified 894,240 held-out plus 231,840 development replay records, 46 scenarios, and 10,000 paired
whole-item bootstrap draws. All tasks are reused audited E06 synthetic tasks; the held-out cohort has
81 distinct items, with 21 development items reported separately. API spend: $0.

Reproduce from this folder (Python 3.10+, standard library; no keys):

```powershell
python build_items.py --check
python freeze.py --check
python -m unittest test_e02 -v
python run.py --full --cohort heldout
python analyse.py --run results/heldout --out analysis/heldout
python run.py --full --cohort development
python analyse.py --run results/development --out analysis/development
python build_report.py
python verify_results.py
python freeze.py --check
```

Figure generation needs optional Matplotlib (requirements-dev.txt) and reuses E06's included Inter font:

```powershell
python figures-post/make_figures.py --analysis analysis/heldout
```

The runner resumes hash-verified shards. Analysis rebuilds every ledger row and can take several minutes.
The reporting supplement formats root documents without changing the approved analytical sources.
Read the limits: costs/time are modelled proxies; failures are assumed; retries reuse saved responses;
this does not measure production failure rates, billing, real queues or universal policy superiority.
