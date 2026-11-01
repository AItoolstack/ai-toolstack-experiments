"""Boundary, correctness, pairing and tamper tests. All fixtures are development or synthetic."""

import copy
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import freeze
from analysis_e2 import METRICS, bootstrap_vectors, outcome, score_records, verified_rows
from e2core import canonical, config, default_response, detect, load_inputs, sha, write_json
from engine import scenarios, should_inject, simulate, uniform
from pilot_fixtures import diagnostic_rows
from run import execute, run_spec


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_inputs()
        cls.cfg = config()

    def run_case(self, design, regime="control", rate=0.0, kind=None, seed=1, ident="inv01", primary=None):
        task = self.data.items[ident]["task"]
        p = primary or self.data.runs[self.cfg["primary"]][ident, 0]
        f = self.data.runs[self.cfg["fallback"]][ident, 0]
        scenario = {"id": "fixture", "regime": regime, "rate": rate, "failure": kind}
        refs = (self.data.refs[self.cfg["primary"], ident, 0], self.data.refs[self.cfg["fallback"], ident, 0])
        return simulate(task, ident, 0, seed, scenario, design, "zero_numeric", p, f, refs, self.cfg)

    def test_zero_rate_all_policies_use_one_unchanged_answer(self):
        for design in self.cfg["designs"]:
            row = self.run_case(design)
            self.assertEqual(row["calls"], 1)
            self.assertEqual(row["backoff_seconds"], 0)
            self.assertEqual(row["output"], {"kind": "source", "model": "oss-20b", "repeat": 0})

    def test_complete_failure_all_five_kinds_all_tasks_have_fixed_terminal_limits(self):
        expected = {
            "default": (1, "default", 0),
            "retry": (3, "default", 3),
            "fallback": (3, "unavailable", 1),
            "say_so": (2, "unavailable", 1),
        }
        for ident in ("inv01", "tl01", "rl01"):
            for kind in self.cfg["failure_types"]:
                for design, (calls, terminal, backoff) in expected.items():
                    with self.subTest(ident=ident, kind=kind, design=design):
                        row = self.run_case(design, "independent", 1.0, kind, ident=ident)
                        self.assertEqual(
                            (row["calls"], row["output"]["kind"], row["backoff_seconds"]), (calls, terminal, backoff)
                        )
                        self.assertTrue(all(e["injected"] == kind and e["observed_failure"] for e in row["events"]))
                        self.assertLessEqual(row["cost_low_usd"], row["cost_high_usd"])

    def test_retry_recovers_only_on_nonfailed_attempt(self):
        s = {"regime": "independent", "rate": 0.2}
        seed = next(
            n
            for n in range(10000)
            if should_inject(s, n, "inv01", 0, "primary", 0) and not should_inject(s, n, "inv01", 0, "primary", 1)
        )
        row = self.run_case("retry", "independent", 0.2, "timeout", seed)
        self.assertEqual(row["calls"], 2)
        self.assertEqual(row["output"]["kind"], "source")
        latency = self.data.runs["oss-20b"]["inv01", 0]["latency_s"]
        self.assertAlmostEqual(row["latency_seconds"], 30 + 1 + latency)

    def test_persistent_primary_and_shared_fallback_differ(self):
        s = {"regime": "persistent_primary", "rate": 0.2}
        seed = next(
            n
            for n in range(10000)
            if should_inject(s, n, "inv01", 0, "primary", 0) and not should_inject(s, n, "inv01", 0, "fallback", 0)
        )
        isolated = self.run_case("fallback", "persistent_primary", 0.2, "timeout", seed)
        shared = self.run_case("fallback", "persistent_shared", 0.2, "timeout", seed)
        self.assertEqual(isolated["output"], {"kind": "source", "model": "sol", "repeat": 0})
        self.assertEqual(shared["output"]["kind"], "unavailable")
        self.assertEqual(self.run_case("retry", "persistent_primary", 0.2, "timeout", seed)["calls"], 3)

    def test_schedule_nesting_order_independence_and_policy_pairing(self):
        low = {"regime": "independent", "rate": 0.01}
        high = {"regime": "independent", "rate": 0.2}
        for seed in range(300):
            self.assertFalse(
                should_inject(low, seed, "inv01", 0, "primary", 0)
                and not should_inject(high, seed, "inv01", 0, "primary", 0)
            )
        self.assertGreaterEqual(uniform(3, "inv01"), 0)
        self.assertLess(uniform(3, "inv01"), 1)
        first = [self.run_case(d, "independent", 0.2, "timeout")["events"][0] for d in self.cfg["designs"]]
        self.assertTrue(all(row == first[0] for row in first))

    def test_native_cutoff_is_never_healed_by_saved_response_reuse(self):
        p = copy.deepcopy(self.data.runs["oss-20b"]["inv01", 0])
        p["finish_reason"] = "length"
        retry = self.run_case("retry", primary=p)
        self.assertEqual(retry["calls"], 3)
        self.assertEqual(retry["output"]["kind"], "default")
        self.assertTrue(all(e["native_fault"] == "cutoff" and e["injected"] is None for e in retry["events"]))

    def test_observable_detector_never_uses_gold(self):
        wrong = copy.deepcopy(self.data.runs["oss-20b"]["inv01", 0])
        obj = json.loads(wrong["content"])
        obj["amount_due"] = 999999
        wrong["content"] = canonical(obj)
        self.assertIsNone(detect("invoice", wrong))
        emitted = self.run_case("say_so", primary=wrong)
        self.assertEqual(emitted["output"]["kind"], "source")
        self.assertEqual(outcome(emitted, self.data.items["inv01"], wrong), "wrong")

    def test_valid_native_tool_with_empty_text_is_not_empty(self):
        row = {
            "content": "",
            "finish_reason": "tool_calls",
            "tool_calls": [{"name": "get_order", "arguments": '{"order_id":"SYNTHETIC-1"}'}],
        }
        self.assertIsNone(detect("tool", row))
        row["tool_calls"][0]["arguments"] = "{broken"
        self.assertEqual(detect("tool", row), "bad_arguments_json")
        row["tool_calls"] = []
        self.assertEqual(detect("tool", row), "empty")

    def test_tool_default_no_call_key_is_unverified(self):
        item = {"task": "tool", "gold": {"call": None}}
        record = {"output": {"kind": "default"}}
        self.assertEqual(outcome(record, item, default_response("tool", "zero_numeric")), "unverified")
        item["gold"]["call"] = "get_order"
        self.assertEqual(outcome(record, item, default_response("tool", "zero_numeric")), "wrong")

    def test_cost_time_and_call_accounting_at_timeout_exhaustion(self):
        row = self.run_case("retry", "persistent_shared", 1.0, "timeout")
        self.assertEqual(row["latency_seconds"], 93)
        self.assertEqual(row["cost_low_usd"], 0)
        self.assertGreater(row["cost_high_usd"], 0)
        self.assertEqual(row["accepted_response_usd"], 0)
        self.assertEqual(row["calls"], len(row["events"]))

    def test_cutoff_cost_uses_cap_and_reasoning_is_not_double_counted(self):
        row = self.run_case("default", "independent", 1.0, "cutoff")
        source = self.data.runs["oss-20b"]["inv01", 0]
        expected = (source["prompt_tokens"] * 0.075 + 2000 * 0.30) / 1e6
        self.assertAlmostEqual(row["cost_high_usd"], expected)
        self.assertEqual(row["cost_low_usd"], row["cost_high_usd"])

    def test_default_sensitivity_changes_only_invoice_numeric_fields(self):
        a = json.loads(default_response("invoice", "zero_numeric")["content"])
        b = json.loads(default_response("invoice", "all_null")["content"])
        self.assertEqual(
            {key for key in a if a[key] != b[key]}, {"net_total", "tax_total", "gross_total", "amount_due"}
        )
        self.assertEqual(default_response("rules", "zero_numeric"), default_response("rules", "all_null"))

    def test_wrong_transition_accounting_uses_same_initial_response(self):
        row = self.run_case("default", "independent", 1.0, "timeout")
        row["scenario"] = "fixture"
        _, stats, _, _, _, _, n = score_records(iter([row]), self.data, self.cfg)
        stat = stats["fixture", "zero_numeric", "default", "all"]
        self.assertEqual(n, 1)
        self.assertEqual(stat["outcomes"]["wrong"], 1)
        self.assertEqual(stat["transitions"]["introduced_wrong"], 1)

    def test_paired_bootstrap_keeps_constant_difference(self):
        vectors = {
            "default": [[0.0] * len(METRICS), [1.0] * len(METRICS)],
            "say_so": [[0.2] * len(METRICS), [1.2] * len(METRICS)],
        }
        result = bootstrap_vectors(vectors, [[0, 0], [0, 1], [1, 1]])
        for a, b in zip(result["say_so"]["wrong"], result["default"]["wrong"], strict=True):
            self.assertAlmostEqual(a - b, 200)

    def test_input_health_and_expected_pilot_coverage(self):
        self.assertEqual(sum(m["rows"] for m in self.data.health.values()), 1428)
        self.assertEqual(self.data.health["glm-flash"]["observable_faults"]["cutoff"], 1)
        self.assertEqual(len(list(scenarios(self.cfg))), 46)
        self.assertLessEqual(set(self.cfg["pilot_ids"]), set(self.data.cohorts["development"]))

    def test_scripted_diagnostics_exercise_recovery_without_changing_study_schedules(self):
        rows = list(diagnostic_rows(self.data, self.cfg))
        self.assertEqual(len(rows), 600)
        self.assertEqual({r["item"] for r in rows}, set(self.cfg["pilot_ids"]))
        expected = {
            "first_primary_only": {
                "default": (1, "default"),
                "retry": (2, "source"),
                "fallback": (2, "source"),
                "say_so": (2, "source"),
            },
            "all_primary": {
                "default": (1, "default"),
                "retry": (3, "default"),
                "fallback": (3, "source"),
                "say_so": (2, "unavailable"),
            },
            "all_calls": {
                "default": (1, "default"),
                "retry": (3, "default"),
                "fallback": (3, "unavailable"),
                "say_so": (2, "unavailable"),
            },
        }
        for row in rows:
            self.assertEqual((row["calls"], row["output"]["kind"]), expected[row["scenario"]][row["design"]])
            self.assertIsNotNone(row["events"][0]["injected"])
        self.assertEqual(len(list(scenarios(self.cfg))), 46)

    def test_resume_hash_guard_and_changed_spec_guard(self):
        spec = run_spec(self.data, self.cfg, True, "development", "test-review")
        spec["scenarios"] = spec["scenarios"][:1]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            execute(path, spec, self.data)
            progress = (path / "progress.json").read_bytes()
            execute(path, spec, self.data)
            self.assertEqual(progress, (path / "progress.json").read_bytes())
            changed = copy.deepcopy(spec)
            changed["tracks"] = [1]
            with self.assertRaisesRegex(ValueError, "Resume refused"):
                execute(path, changed, self.data)
            target = next((path / "shards").glob("*.gz"))
            target.write_bytes(target.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "Saved shard changed"):
                execute(path, spec, self.data)

    def test_full_pilot_roundtrip_and_semantic_tamper_detection(self):
        spec = run_spec(self.data, self.cfg, True, "development", "test-review")
        with tempfile.TemporaryDirectory() as temp, patch("analysis_e2.check", return_value="test-review"):
            path = Path(temp)
            execute(path, spec, self.data)
            _, _, rows = verified_rows(path, self.data)
            self.assertEqual(sum(1 for _ in rows), 3680)
            target = sorted((path / "shards").glob("*.gz"))[0]
            with gzip.open(target, "rt", encoding="utf-8") as stream:
                contents = [json.loads(line) for line in stream]
            contents[0]["cost_high_usd"] = 999
            with gzip.open(target, "wt", encoding="utf-8") as stream:
                stream.write("".join(canonical(row) + "\n" for row in contents))
            progress = json.loads((path / "progress.json").read_text(encoding="utf-8"))
            progress["shards"][target.name]["sha256"] = sha(target)
            write_json(path / "progress.json", progress)
            _, _, rows = verified_rows(path, self.data)
            with self.assertRaisesRegex(ValueError, "Replay/accounting/coverage mismatch"):
                list(rows)

    def test_full_run_requires_matching_explicit_approval(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(freeze, "ROOT", Path(temp)),
            patch.object(freeze, "check", return_value="review-A"),
        ):
            with self.assertRaisesRegex(ValueError, "Full evaluation blocked"):
                freeze.require_approval()
            write_json(
                Path(temp) / "APPROVAL.json", {"review_sha256": "review-B", "approved_by": "Tej", "note": "fixture"}
            )
            with self.assertRaisesRegex(ValueError, "Approval does not bind"):
                freeze.require_approval()
            write_json(
                Path(temp) / "APPROVAL.json", {"review_sha256": "review-A", "approved_by": "Tej", "note": "fixture"}
            )
            self.assertEqual(freeze.require_approval(), "review-A")


if __name__ == "__main__":
    unittest.main()
