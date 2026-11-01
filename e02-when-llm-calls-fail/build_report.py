"""Reporting-only supplement: turn the unchanged approved analyses into reader artifacts.

Added after approval, outside the frozen inference/scoring protocol. No new inference,
policy, task, seed, judge, confidence calculation or exploratory arm is introduced.
"""

from __future__ import annotations

import json
from pathlib import Path

from e2core import ROOT, config, sha, write_json
from freeze import require_approval

KINDS = ("rate_limit", "timeout", "cutoff", "malformed_json", "empty")
DESIGNS = ("default", "retry", "fallback", "say_so")
LABELS = {"default": "Default", "retry": "Retry", "fallback": "Fallback", "say_so": "Say so"}
OUTCOMES = ("correct", "wrong", "unverified", "couldnt_check")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_analyses(review):
    analyses = {}
    for cohort in ("heldout", "development"):
        directory = ROOT / "analysis" / cohort
        verification = read_json(directory / "verification.json")
        if verification["review_sha256"] != review or not verification["all_rows_replayed_and_compared"]:
            raise ValueError("Analysis does not match approved/replayed evidence: " + cohort)
        for name, expected in verification["output_sha256"].items():
            if sha(directory / name) != expected:
                raise ValueError("Analysis changed: " + str(directory / name))
        summary, uncertainty = read_json(directory / "summary.json"), read_json(directory / "uncertainty.json")
        if summary["mode"] != "approved_evaluation" or summary["cohort"] != cohort:
            raise ValueError("Not the approved full cohort")
        if uncertainty["method"]["draws"] != 10000 or uncertainty["method"]["pilot_diagnostic_only"]:
            raise ValueError("Expected full frozen uncertainty analysis")
        analyses[cohort] = {
            "summary": summary["scenarios"],
            "uncertainty": uncertainty["scenarios"],
            "example": read_json(directory / "example.json"),
            "verification": verification,
        }
    return analyses


def path_for(scenario, design, *fields, cohort="heldout", variant="zero_numeric", scope="all"):
    return {"file": f"analysis/{cohort}/summary.json", "path": ["scenarios", scenario, variant, scope, design, *fields]}


def resolve(source):
    value = read_json(ROOT / source["file"])
    for component in source["path"]:
        value = value[component]
    return value


def source_label(source):
    return source["file"] + "::" + ".".join(source["path"])


def row_for(analyses, scenario, design, cohort="heldout", variant="zero_numeric", scope="all"):
    return analyses[cohort]["summary"][scenario][variant][scope][design]


def fmt_ci(interval):
    return f"{interval[0]:.2f} to {interval[1]:.2f}"


def table(analyses, scenario, cohort="heldout"):
    lines = [
        "| Design | Correct | Wrong | Unverified | Couldn't check | Wrong / 1,000 (95% item CI) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for design in DESIGNS:
        row = row_for(analyses, scenario, design, cohort)
        n = row["denominator_replays"]
        counts = " | ".join(f"{row['counts'][metric]}/{n}" for metric in OUTCOMES)
        ci = analyses[cohort]["uncertainty"][scenario]["zero_numeric"]["all"][design]["wrong_per_1000"]
        lines.append(f"| {LABELS[design]} | {counts} | {ci['point']:.2f} ({fmt_ci(ci['item_ci95'])}) |")
    return lines


def cost_table(analyses, scenario):
    lines = [
        "| Design | Calls | Calls/task | USD proxy/1,000 | Mean modelled s | Added vs 0% (s) | Modelled p95 s |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for design in DESIGNS:
        row = row_for(analyses, scenario, design)
        p = row["point"]
        added = analyses["heldout"]["uncertainty"][scenario]["zero_numeric"]["all"][design]["mean_latency_seconds"][
            "minus_own_control"
        ]["point"]
        lines.append(
            f"| {LABELS[design]} | {row['total_calls']} | {p['mean_calls']:.4f} | "
            f"{p['cost_low_usd_per_1000']:.5f} to {p['cost_high_usd_per_1000']:.5f} | "
            f"{p['mean_latency_seconds']:.3f} | {added:.3f} | {row['modelled_p95_seconds']:.3f} |"
        )
    return lines


def claim(ident, text, sources):
    return {"id": ident, "text": text, "sources": [{**source, "value": resolve(source)} for source in sources]}


def claims_for(analyses):
    independent, primary, shared = (
        "independent-20-timeout",
        "persistent_primary-20-timeout",
        "persistent_shared-20-timeout",
    )
    d, r, f, s = [row_for(analyses, independent, design) for design in DESIGNS]
    n = d["denominator_replays"]
    claims = [
        claim(
            "independent-timeout",
            f"Under assumed independent 20% timeouts, default showed "
            f"{d['counts']['wrong']}/{n} wrong completed results ({d['point']['wrong_per_1000']:.2f} per 1,000); "
            f"retry showed {r['counts']['wrong']}/{n} ({r['point']['wrong_per_1000']:.2f} per 1,000).",
            [
                path_for(independent, design, *fields)
                for design in ("default", "retry")
                for fields in (("counts", "wrong"), ("denominator_replays",), ("point", "wrong_per_1000"))
            ],
        )
    ]
    claims.append(
        claim(
            "say-so-tradeoff",
            f"In that same scenario, say-so showed {s['counts']['wrong']}/{n} wrong "
            f"results, returned couldn't-check {s['counts']['couldnt_check']}/{n} times, "
            f"and used {s['total_calls']} calls; fallback showed {f['counts']['wrong']}/{n} wrong "
            f"and {f['counts']['couldnt_check']}/{n} couldn't-check results "
            f"using {f['total_calls']} calls.",
            [
                path_for(independent, design, *fields)
                for design in ("say_so", "fallback")
                for fields in (
                    ("counts", "wrong"),
                    ("counts", "couldnt_check"),
                    ("total_calls",),
                    ("denominator_replays",),
                )
            ],
        )
    )
    r, f = [row_for(analyses, primary, design) for design in ("retry", "fallback")]
    claims.append(
        claim(
            "persistent-primary",
            f"When a 20% task-level failure episode persisted on primary, "
            f"retry showed {r['counts']['wrong']}/{n} wrong completed results while fallback showed "
            f"{f['counts']['wrong']}/{n}; their calls were {r['total_calls']} and {f['total_calls']}. "
            "This tests an assumed persistent episode, not a measured rate-limit storm.",
            [
                path_for(primary, design, *fields)
                for design in ("retry", "fallback")
                for fields in (("counts", "wrong"), ("total_calls",), ("denominator_replays",))
            ],
        )
    )
    f, s = [row_for(analyses, shared, design) for design in ("fallback", "say_so")]
    claims.append(
        claim(
            "shared-failure",
            f"When the same 20% episode also blocked fallback, fallback and say-so "
            f"had identical outcome counts: {f['counts']}. Fallback used {f['total_calls']} calls versus "
            f"{s['total_calls']} for say-so across {n} replays. This equality follows the shared-failure model.",
            [
                path_for(shared, design, *fields)
                for design in ("fallback", "say_so")
                for fields in (("counts",), ("total_calls",), ("denominator_replays",))
            ],
        )
    )
    return claims


def build():
    review = require_approval()
    analyses = load_analyses(review)
    h = analyses["heldout"]
    independent, primary, shared = (
        "independent-20-timeout",
        "persistent_primary-20-timeout",
        "persistent_shared-20-timeout",
    )
    control = row_for(analyses, "control", "default")
    n = control["denominator_replays"]
    claims = claims_for(analyses)
    for claim_record in claims:
        for source in claim_record["sources"]:
            if resolve(source) != source["value"]:
                raise ValueError("Claim source mismatch")
    write_json(ROOT / "claims.json", claims)
    lines = [
        "# E02: what happens when an LLM call fails?",
        "",
        "**Completed approved offline evaluation, 1 November 2026.** No API calls or business tools executed.",
        "These are scenario-conditional replay results, not observed production failure rates or provider reliability.",
        "",
        "## What was run",
        "",
        "The approved E06 OSS-20B -> Sol response pair, unchanged audited synthetic tasks, 46 failure scenarios,",
        "two default variants, ten seeds and three saved primary-response tracks. Retries reuse a saved answer.",
        "The headline uses 81 reused E06 held-out items (29 invoices, 29 tools, 23 rules), not a newly unseen E02 set.",
        f"Each design/scenario/variant has {n} replay outcomes on those 81 distinct items.",
        "894,240 held-out ledger records and 231,840 development ledger records were rebuilt and verified.",
        "Seeds, repeats, failure kinds and scenarios do not create independent items.",
        "The 21 E06 development items are reported separately below. Scripted pilot fixtures are excluded.",
        "",
        "## Findings supported by these scenarios",
        "",
    ]
    for item in claims:
        lines += [f"- {item['text']} See `claims.json::{item['id']}` for exact file/field/value references."]
    lines += [
        "",
        "## No injected failures: the underlying model still makes mistakes",
        "",
        f"The 0% control has {control['counts']['wrong']}/{n} wrong completed responses "
        f"({control['point']['wrong_per_1000']:.2f} per 1,000).",
        "Every design uses the same first response in this control. Recovery policies only act on detected",
        "failures; say-so cannot intercept an accepted factual mistake. Replaying each saved response across",
        "ten seeds repeats that response rather than supplying ten independent model observations.",
        "Source: `analysis/heldout/summary.json::scenarios.control.zero_numeric.all.default`.",
        "",
        "## Independent 20% timeouts",
        "",
        *table(analyses, independent),
        "",
        "Counts have a shared replay denominator, not 2,430 independent examples. Unverified tool no-ops are",
        "excluded from wrong and from correct.",
        "The possible misleading-completion count is [wrong, wrong + unverified].",
        "A numerically correct default still does not establish that a check completed.",
        "",
        *cost_table(analyses, independent),
        "",
        "USD ranges are historical token-price scenario proxies, not guarantees about failed-call billing.",
        "Timeout attempts are assumed to take 30s. Means and p95 are modelled, not measured service latency.",
        "Backoff is 1s then 2s. Native saved-response durations proxy healthy attempts.",
        f"Source subtree: `analysis/heldout/summary.json::scenarios.{independent}.zero_numeric.all`.",
        "",
        "### Paired differences against default",
        "",
        "| Design | Wrong / 1,000 difference (95% paired item CI) | Correct / 1,000 difference (95% paired item CI) |",
        "| --- | --- | --- |",
    ]
    for design in DESIGNS[1:]:
        u = h["uncertainty"][independent]["zero_numeric"]["all"][design]
        wrong, correct = u["wrong_per_1000"]["minus_default"], u["correct_per_1000"]["minus_default"]
        lines.append(
            f"| {LABELS[design]} | {wrong['point']:.2f} ({fmt_ci(wrong['item_ci95'])}) | "
            f"{correct['point']:.2f} ({fmt_ci(correct['item_ci95'])}) |"
        )
    lines += [
        "",
        "These 95% percentile intervals use 10,000 task-stratified paired whole-item draws, seed 20261102.",
        "They retain every seed/track within an item. They do not capture template dependence, unmeasured",
        "fallback sampling variation, or uncertainty in the assumed failure/cost/latency/default model.",
        "Do not infer a policy ranking from overlapping marginal intervals; use the paired comparison and context.",
        "Source: `analysis/heldout/uncertainty.json::scenarios.independent-20-timeout.zero_numeric.all.<design>`.",
        "",
        "## Persistent primary failures: retries have a limit",
        "",
        *table(analyses, primary),
        "",
        *cost_table(analyses, primary),
        "",
        "A triggered primary episode blocks every primary attempt by construction. An independent fallback",
        "can still fail or answer incorrectly. Extra retries cannot heal an episode defined to outlast the task.",
        "",
        "## Shared failures: fallback can add work without changing outcomes",
        "",
        *table(analyses, shared),
        "",
        *cost_table(analyses, shared),
        "",
        "The shared-episode equality of fallback/say-so outcomes is a consequence of the model, not an",
        "empirical discovery about the two historical providers.",
        "This does not model queues or retry-caused congestion.",
        "",
        "## All prespecified rates and regimes",
        "",
        "The compact table uses timeout and zero-numeric defaults; all five kinds and both variants remain in JSON.",
        "",
        "| Regime | Nominal rate | Design | Wrong / replays | Couldn't check / replays | Calls |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for regime in config()["regimes"]:
        for rate in (1, 5, 20):
            scenario = f"{regime}-{rate:02d}-timeout"
            for design in DESIGNS:
                r = row_for(analyses, scenario, design)
                lines.append(
                    f"| {regime} | {rate}% | {LABELS[design]} | {r['counts']['wrong']}/{n} | "
                    f"{r['counts']['couldnt_check']}/{n} | {r['total_calls']} |"
                )
    lines += [
        "",
        "Independent rates are per-attempt probabilities; persistent rates are per-task episode probabilities.",
        "Realized initial/attempt rates are exported. Each case's seed-level mean min/max is Monte Carlo spread,",
        "not an item confidence interval. Do not average these scenarios into a production failure estimate.",
        "",
        "## Failure kinds and default sensitivity",
        "",
        "All five injected failure kinds are detectable and share trigger draws and recovery rules. Accordingly,",
        "equal outcome counts across kinds are not five independent confirmations of an accuracy result.",
        "Cost/time differences depend on the prespecified failure proxies (429 0.2s, timeout 30s, cutoff cap).",
        "The null-numeric invoice sensitivity retains its own results; whole-task grading can hide differences",
        "between individual fields of equally wrong default records. Other defaults are outside this comparison.",
        "",
        "## Worked example selected by the frozen rule",
        "",
    ]
    example = h["example"]
    if example:
        selected = example["selection"]
        lines += [
            f"Selected **{selected['item']}**, seed {selected['seed']}, track {selected['track']}, "
            f"scenario {selected['scenario']}. It is the first held-out baseline-correct -> wrong default",
            "at independent 5% timeout, sorted by item ID, seed and track. All qualifying records are in",
            "`analysis/heldout/example-candidates.jsonl`; full task, key, visible replies and source lines are",
            "in `analysis/heldout/example.json`.",
            "",
            "| Design | Visible outcome | Calls | Modelled seconds |",
            "| --- | --- | --- | --- |",
        ]
        for paired in example["paired_designs"]:
            r = paired["record"]
            lines.append(f"| {LABELS[r['design']]} | {paired['grade']} | {r['calls']} | {r['latency_seconds']:.2f} |")
    else:
        lines += ["No held-out record met the frozen example rule. No substitute was selected."]
    lines += [
        "",
        "## Separate development cohort",
        "",
        *table(analyses, independent, "development"),
        "",
        "21 development items; 630 replay outcomes per design/scenario/variant; excluded from headline estimates.",
        "Source: `analysis/development/summary.json::scenarios.independent-20-timeout.zero_numeric.all`.",
        "",
        "## Limits and publication boundaries",
        "",
        "Short synthetic tasks; shared invoice templates and policy text; one primary/fallback pair; one saved",
        "fallback response per item; repeated primary responses reused on retries; coarse grading of tool prose;",
        "assumed defaults, failure probabilities, correlation, durations and failed-call costs; no business execution.",
        "Independent retry improvement follows the failure model. The empirical content is how the saved model",
        "mistakes and task defaults interact with those assumptions. This does not establish production prevalence,",
        "real retry recovery, universal safety, billed cost, queue behaviour or a universally best design.",
        "",
        "## Evidence and reproduction",
        "",
        "- `FREEZE.json` plus `APPROVAL.json`: exact approved design/input/source hashes and chat approval.",
        "- `results/<cohort>/run.json`, `progress.json`, `shards/`: every schedule, attempt and output reference.",
        "- `analysis/<cohort>/verification.json`: verified ledger counts, inputs and output hashes.",
        "- `analysis/<cohort>/summary.json`, `uncertainty.json`: counts, means and intervals by scenario/task/variant.",
        "- `claims.json`, `RESULTS.md`: exact numerical claim sources, including the outer `scenarios` key.",
        "- `REPORTING.json`: this reporting supplement and its inputs/outputs; approved analytical code is unchanged.",
        "- `README-RESULTS.md`: reader entry point and PowerShell reproduction commands.",
        "",
    ]
    write_md("FULL-RESULTS.md", lines)
    mapping = ["# E02 claim-to-source map", "", "All claims are conditional on the stated scenario.", ""]
    for item in claims:
        mapping += [f"## {item['id']}", "", item["text"], ""]
        for source in item["sources"]:
            mapping.append(f"- `{source_label(source)}` = `{json.dumps(source['value'], sort_keys=True)}`")
        mapping += [""]
    write_md("RESULTS.md", mapping)
    handover = [
        "# E02 handover for the post",
        "",
        "Completed 1 November 2026. Do not write a production-failure-rate claim.",
        "Use 81 distinct held-out items; 2,430 is the repeated replay denominator in each scenario.",
        "Development results and scripted diagnostic fixtures stay separate.",
        "",
        "## Four supported claims",
        "",
    ]
    for item in claims:
        handover += [f"- {item['text']} Exact sources: `RESULTS.md`, section `{item['id']}`, and `claims.json`."]
    handover += ["", "## Concrete example", ""]
    if example:
        handover += [
            f"Use **{example['selection']['item']}** from `analysis/heldout/example.json`. The frozen rule selected",
            "the first held-out baseline-correct -> wrong default at independent 5% timeout,",
            "ordered by item, seed and track.",
            "The synthetic source and audited key are in `synthetic_task`; visible replies and source file/line",
            "references are in `paired_designs`. Do not replace this with a more dramatic case.",
            "",
            "Audited expected output: `"
            + json.dumps(example["synthetic_task"]["gold"], ensure_ascii=False, sort_keys=True)
            + "`.",
            "",
        ]
        for paired in example["paired_designs"]:
            r = paired["record"]
            response = paired["visible_response"]
            handover += [
                f"- {LABELS[r['design']]}: {paired['grade']}; {r['calls']} calls; "
                f"{r['latency_seconds']:.2f} modelled seconds. Visible response: "
                f"`{json.dumps(response, ensure_ascii=False, sort_keys=True)}`"
            ]
    else:
        handover += ["No record met the frozen example rule; do not substitute another example."]
    handover += [
        "",
        "## What not to claim",
        "",
        "- No measured provider failure rates, real retry sampling, live storm/queue behaviour, or billed spend.",
        "- No universal policy winner or proof that a structurally valid response is correct.",
        "- No extra independent examples from the ten seeds, three tracks, five failure kinds or two default variants.",
        "- No claim that an accidentally correct default proves a check completed, or a silent no-op is useful help.",
        "- No hidden ranking from overlapping marginal intervals. Pairwise default comparisons and conditional",
        "  whole-item intervals are in the uncertainty file; templates/failure assumptions remain outside them.",
        "",
        "## Figures and reader sources",
        "",
        "Use figures-post/e02-recovery-flow.png and e02-wrong-results.png with their captions/metadata.",
        "Use FIGURE-CAPTIONS.md for denominators, intervals, normalization and alt text.",
        "Use root FULL-RESULTS.md and RESULTS.md as the reviewed narrative and exact claim map. Generated",
        "cohort-local report stubs are retained for reproducibility; their shorthand paths omit the outer",
        "`scenarios` JSON key, which the root map and claims.json include explicitly.",
        "This is a handover, not the blog post. All task data is fictional; no employer/client names.",
        "",
    ]
    write_md("HANDOVER-FOR-POST.md", handover)
    captions = [
        "# E02 figure captions and alt text",
        "",
        "## Recovery flow",
        "",
        "A failed primary call enters one of four designs: emit a completed default; retry up to twice",
        "then default; retry once then use fallback; or retry once then explicitly say couldn't check.",
        "A usable response ends recovery early; failed fallback also emits couldn't check.",
        "Policy diagram only, with no measured outcome claim.",
        "",
        "## Wrong completed results",
        "",
        "Assumed independent 20% timeouts, zero-numeric defaults, 81 reused E06 held-out synthetic items.",
        "Ten seeds and three primary tracks give 2,430 paired replay outcomes per design, not 2,430",
        "independent items. Bars show wrong completed results per 1,000 tasks; intervals are 95%",
        "task-stratified whole-item bootstrap intervals conditional on the saved answers and failure model.",
        "",
    ]
    for design in DESIGNS:
        row = row_for(analyses, independent, design)
        ci = h["uncertainty"][independent]["zero_numeric"]["all"][design]["wrong_per_1000"]["item_ci95"]
        captions.append(
            f"- {LABELS[design]}: {row['counts']['wrong']}/{n} wrong completed results; "
            f"{row['point']['wrong_per_1000']:.2f} per 1,000; 95% interval {fmt_ci(ci)}."
        )
    captions += [
        "",
        "Unverified tool defaults are excluded from wrong and correct, and reported separately.",
        "Saying couldn't check can withhold correct answers; do not compare these bars without the coverage table.",
        "The close recovery-policy estimates do not establish a ranking. These are not provider failure rates.",
        "Source: analysis/heldout/summary.json and uncertainty.json,",
        "scenarios.independent-20-timeout.zero_numeric.all.<design>.",
        "",
    ]
    write_md("FIGURE-CAPTIONS.md", captions)
    write_md(
        "README-RESULTS.md",
        [
            "# E02: completed results",
            "",
            "**Current status: approved offline evaluation complete, 1 November 2026. Ready for review and Git push.**",
            "",
            "Start with [FULL-RESULTS.md](FULL-RESULTS.md), [RESULTS.md](RESULTS.md), and",
            "[HANDOVER-FOR-POST.md](HANDOVER-FOR-POST.md). The approved protocol is [DESIGN.md](DESIGN.md).",
            "",
            "The original README.md, DESIGN.md and REVIEW-CHECKLIST.md are retained byte-for-byte as historical",
            "parts of the approved snapshot. Their pre-run status statements describe the moment of that snapshot.",
            "APPROVAL.json and this results entry point record the subsequent approval and completion.",
            "",
            "Verified 894,240 held-out plus 231,840 development replay records, 46 scenarios, and 10,000 paired",
            "whole-item bootstrap draws. All tasks are reused audited E06 synthetic tasks; the held-out cohort has",
            "81 distinct items, with 21 development items reported separately. API spend: $0.",
            "",
            "Reproduce from this folder (Python 3.10+, standard library; no keys):",
            "",
            "```powershell",
            "python build_items.py --check",
            "python freeze.py --check",
            "python -m unittest test_e02 -v",
            "python run.py --full --cohort heldout",
            "python analyse.py --run results/heldout --out analysis/heldout",
            "python run.py --full --cohort development",
            "python analyse.py --run results/development --out analysis/development",
            "python build_report.py",
            "python verify_results.py",
            "python freeze.py --check",
            "```",
            "",
            "Figure generation needs optional Matplotlib (requirements-dev.txt) and reuses E06's included Inter font:",
            "",
            "```powershell",
            "python figures-post/make_figures.py --analysis analysis/heldout",
            "```",
            "",
            "The runner resumes hash-verified shards. Analysis rebuilds every ledger row and can take several minutes.",
            "The reporting supplement formats root documents without changing the approved analytical sources.",
            "Read the limits: costs/time are modelled proxies; failures are assumed; retries reuse saved responses;",
            "this does not measure production failure rates, billing, real queues or universal policy superiority.",
            "",
        ],
    )
    write_json(
        ROOT / "REPORTING.json",
        {
            "status": "COMPLETED_REPORTING_ONLY_SUPPLEMENT",
            "review_sha256": review,
            "report_source_sha256": sha(Path(__file__)),
            "analysis_verification_sha256": {
                cohort: sha(ROOT / "analysis" / cohort / "verification.json") for cohort in analyses
            },
            "outputs": {
                name: sha(ROOT / name)
                for name in (
                    "FULL-RESULTS.md",
                    "RESULTS.md",
                    "HANDOVER-FOR-POST.md",
                    "README-RESULTS.md",
                    "FIGURE-CAPTIONS.md",
                    "claims.json",
                )
            },
            "note": "Approved protocol/code unchanged. This supplement formats existing frozen metrics and sources.",
        },
    )
    print("Wrote completed reader results, four source-checked claims, post handover and reporting manifest.")


def write_md(name, lines):
    (ROOT / name).write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()
