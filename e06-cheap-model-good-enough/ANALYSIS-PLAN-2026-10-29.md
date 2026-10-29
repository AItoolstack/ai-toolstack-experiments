# Offline analysis plan, recorded before full-run accuracy inspection

The experimental items, keys, requests and validators remain frozen. This file specifies
the uncertainty calculations deferred in `PROTOCOL.md`, using saved responses only.

- Primary cohort: the 81 held-out items. Report all 102 and the 21 development items separately.
- Retain every expected saved row, including cutoff, unreadable output and multiple-call
  events, if Tej accepts the explicitly reported health-gate exception. Do not impute reruns.
- Model-alone accuracy is the mean of within-item correctness across its frozen repeats.
  A production-alone policy costs one answer; agreement costs all three cheap answers.
- For each cheap candidate and its two cascades, compare with Sol on the same items.
  The Sol answer is reused, so its own run-to-run variation cannot be estimated.
- Bootstrap whole items, retaining all cheap repeats and the single Sol response together.
  Resample within each task with the observed per-task cohort sizes fixed, then combine
  using those item counts. This preserves the designed task mix and avoids treating calls
  as independent items. Per-task estimates resample only that task's items.
- Use 10,000 draws, fixed seed 6, and percentile 95% intervals (2.5th/97.5th percentiles).
  Report accuracy differences in percentage points, paired cost differences and escalation
  rates. These intervals describe this item set, not the range of customer workflows.
- Invoice templates and shared policy text introduce dependence beyond repeats. Explicitly
  state that item bootstrapping cannot quantify every source of template dependence.
- Keep the frozen exact answer-comparison rule for agreement; wording or representation
  differences may trigger escalation. No claim of semantic equivalence or majority voting.
- Report per-kind and per-trap counts, with both call and distinct-item denominators. Do not
  rank near-tied models or turn deliberately difficult-item accuracy into production accuracy.
- Worked-example rule: enumerate every wrong answer that passes the checks in an evidence
  file; choose the first held-out example by stable item ID for the main explanation rather
  than selecting only the most dramatic response. Discuss key disagreements transparently.
- Preserve source/result hashes, frozen scorer version, run date, and the bootstrap script
  hash alongside derived files. No new inference or key change is permitted by this plan.
