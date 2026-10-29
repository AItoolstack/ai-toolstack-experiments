"""Regression checks for API contracts, failure handling and evaluation denominators. No network or keys."""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import analyse
import pilot_health
import policies
import run
from common import MODELS, load_items, load_tools


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.items = load_items("items_samples.jsonl")
        self.tools = load_tools()
        self.invoice = self.items["inv01"]
        self.tool = self.items["tl01"]

    def row(self, item, model="llama-8b", rep=0):
        class Right:
            def random(self):
                return 0

        return {"model": model, "item": item["id"], "repeat": rep, **run.scripted(item, Right())}

    def test_responses_preserves_low_reasoning_and_optional_tools(self):
        body = run.request_body(MODELS["sol"], self.tool, self.tools)
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertFalse(body["store"])
        self.assertFalse(body["tools"][0]["strict"])
        self.assertEqual(body["tools"][0]["parameters"], self.tools[0]["parameters"])
        self.assertNotIn("parallel_tool_calls", body)  # do not constrain the multiple-call failure away
        self.assertIn("messages", run.request_body(MODELS["llama-8b"], self.tool, self.tools))

    def test_responses_normalises_calls_usage_and_length(self):
        data = {
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
            "output": [{"type": "function_call", "name": "get_order", "arguments": "{}"}],
            "usage": {"input_tokens": 10, "output_tokens": 20, "output_tokens_details": {"reasoning_tokens": 8}},
        }
        row = run.normalise_response(data, "responses")
        self.assertEqual(row["finish_reason"], "length")
        self.assertEqual(row["tool_calls"][0]["name"], "get_order")
        self.assertEqual(row["completion_tokens"], 20)
        self.assertEqual(row["reasoning_tokens"], 8)

    def test_content_not_silently_truncated(self):
        row = run.normalise_response(
            {"choices": [{"message": {"content": "x" * 4000}, "finish_reason": "stop"}]}, "chat/completions"
        )
        self.assertEqual(len(row["content"]), 4000)

    def test_retry_records_cause_redacts_key_and_stops(self):
        key = "private-test-secret"
        diagnostic = []
        with patch("run.urllib.request.urlopen", side_effect=urllib.error.URLError(key)), patch("run.time.sleep"):
            with self.assertRaises(run.StopRun) as error:
                run.call_api(MODELS["llama-8b"], key, self.invoice, self.tools, diagnostic.append)
        self.assertEqual(len(diagnostic), 5)
        self.assertIn("URLError", str(error.exception))
        self.assertNotIn(key, str(diagnostic))
        self.assertFalse(diagnostic[-1]["retrying"])

    def test_http_400_is_not_retried(self):
        error = urllib.error.HTTPError("https://example.test", 400, "Bad Request", {}, io.BytesIO(b"unsupported"))
        with patch("run.urllib.request.urlopen", side_effect=error) as request:
            with self.assertRaisesRegex(run.StopRun, "HTTP 400: unsupported"):
                run.call_api(MODELS["sol"], "private", self.tool, self.tools)
        self.assertEqual(request.call_count, 1)

    def test_process_exits_nonzero_on_failed_work(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("run.results_dir", return_value=Path(tmp)),
            patch("run.load_key", return_value="private"),
            patch("run.call_api", side_effect=run.StopRun("diagnostic failure")),
            patch(
                "sys.argv",
                ["run.py", "--model", "sol", "--items", "items_samples.jsonl", "--only", "inv01", "--repeats", "1"],
            ),
        ):
            with self.assertRaises(SystemExit) as error:
                run.main()
            self.assertEqual(error.exception.code, 1)

    def test_malformed_tool_arguments_are_failures_not_crashes(self):
        for args in ("[]", "null", '"text"', "not JSON"):
            row = {"tool_calls": [{"name": "get_order", "arguments": args}], "content": ""}
            self.assertFalse(analyse.score(self.tool, row)["correct"])
            self.assertFalse(analyse.passes_check(self.tool, row))

    def test_tool_schema_rejects_wrong_types(self):
        row = {"tool_calls": [{"name": "get_order", "arguments": '{"order_id":123}'}]}
        self.assertFalse(analyse.passes_check(self.tool, row))
        self.assertIn("invalid_tool_schema", analyse.score(self.tool, row)["errors"])

    def test_missing_null_field_is_still_missing(self):
        item = next(
            i for i in self.items.values() if i["task"] == "invoice" and any(v is None for v in i["gold"].values())
        )
        row = self.row(item)
        data = json.loads(row["content"])
        field = next(k for k, v in item["gold"].items() if v is None)
        del data[field]
        row["content"] = json.dumps(data)
        self.assertIn("missing:" + field, analyse.score(item, row)["errors"])

    def test_invalid_date_without_due_date_is_rejected(self):
        row = self.row(self.invoice)
        data = json.loads(row["content"])
        data.update(invoice_date="2026-02-30", due_date=None)
        row["content"] = json.dumps(data)
        self.assertTrue(analyse.passes_check(self.invoice, row, "baseline"))
        self.assertFalse(analyse.passes_check(self.invoice, row))

    def test_unparsed_truncated_answer_has_both_flags(self):
        errors = analyse.score(self.invoice, {"content": "{", "finish_reason": "length"})["errors"]
        self.assertEqual(errors, ["unparsed", "cut_off"])

    def test_nonfinite_numbers_are_not_answers(self):
        for value in ("NaN", "Infinity", float("inf"), float("nan"), True):
            self.assertIsNone(analyse.as_number(value))

    def test_one_repeat_is_not_agreement_and_partial_fallback_is_not_a_cohort(self):
        items = {k: self.items[k] for k in ("inv01", "tl01")}
        cheap = {(i, 0): (self.row(item), {"correct": True}) for i, item in items.items()}
        fallback = {("inv01", 0): (self.row(items["inv01"], "sol"), {"correct": True})}
        check = analyse.cascade(items, cheap, fallback, "all", 1, "check", "v2")
        self.assertEqual(check["status"], "incomplete")
        agree = analyse.cascade(items, cheap, cheap, "all", 1, "agreement", "v2")
        self.assertEqual(agree["missing_cheap"], 4)
        invoice = analyse.cascade(items, cheap, fallback, "invoice", 1, "check", "v2")
        self.assertEqual(invoice["status"], "complete")

    def test_three_matching_answers_can_still_be_wrong(self):
        items = {"inv01": self.invoice}
        cheap = {("inv01", r): (self.row(self.invoice, rep=r), {"correct": False}) for r in range(3)}
        fb = {("inv01", 0): (self.row(self.invoice, "sol"), {"correct": True})}
        result = analyse.cascade(items, cheap, fb, "all", 3, "agreement", "v2")
        self.assertEqual(result["accuracy"], 0)
        self.assertEqual(result["escalated"], 0)

    def test_validator_confusion_counts(self):
        pairs = [({"accepted": a}, {"correct": c}) for a, c in ((True, True), (True, False), (False, True))]
        metrics = analyse.check_metrics(pairs, lambda r: r["accepted"])
        self.assertEqual(metrics["wrong_accepted"], 1)
        self.assertEqual(metrics["correct_escalated"], 1)
        self.assertEqual(metrics["accepted_accuracy"], 0.5)

    def test_glm_zero_temperature_is_forwarded_without_changing_default_arm(self):
        default = run.request_body(MODELS["glm-flash"], self.tool, self.tools)
        control = run.request_body(MODELS["glm-flash-t0"], self.tool, self.tools)
        self.assertNotIn("temperature", default)
        self.assertEqual(control["temperature"], 0)
        self.assertEqual(default["provider"], {"order": ["z-ai/fp8"], "allow_fallbacks": False})
        self.assertEqual(default["max_tokens"], 2000)
        self.assertEqual(default["reasoning"], {"effort": "low"})

    def test_single_fallback_is_reused_without_hiding_missing_cheap_repeats(self):
        items = {"inv01": self.invoice}
        cheap = {("inv01", r): (self.row(self.invoice, rep=r), {"correct": False}) for r in range(3)}
        fallback = {("inv01", 0): (self.row(self.invoice, "sol"), {"correct": True})}
        # Force escalation so the fallback lookup is exercised at cheap repeats 1 and 2.
        with patch("analyse.passes_check", return_value=False):
            result = analyse.cascade(items, cheap, fallback, "all", 3, "check", "v2", fallback_repeats=1)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["accuracy"], 1)
            self.assertEqual(result["n"], 3)
            self.assertEqual(result["n_items"], 1)
            self.assertEqual(result["fallback_repeat_policy"], "reuse_repeat_0")
            cheap.pop(("inv01", 2))
            partial = analyse.cascade(items, cheap, fallback, "all", 3, "check", "v2", fallback_repeats=1)
            self.assertEqual(partial["status"], "incomplete")
            self.assertEqual(partial["missing_cheap"], 1)

    def test_budget_uses_single_sol_and_control_and_reports_missing_models(self):
        data = {"task_cost_projection": {
            "invoice": {"projected_usd_one_repeat": 1, "projected_usd_one_repeat_double_output": 2}
        }}
        report = pilot_health.study_projection({"oss-20b": data, "sol": data, "glm-flash-t0": data,
                                               "llama-8b": data})
        self.assertEqual(report["usd"], 5)
        self.assertEqual(report["usd_double_output"], 10)
        self.assertEqual(report["calls"], 510)
        self.assertNotIn("llama-8b", report["models"])
        self.assertFalse(report["complete_model_coverage"])
        self.assertEqual(set(report["missing_models"]), {"luna", "glm-flash", "oss-120b"})

    def test_policy_day_boundaries_and_overrides(self):
        for days, expected in [(14, 0), (15, 2), (28, 2), (29, 5)]:
            self.assertEqual(policies.energy({"days": days, "energy_bill": 100}), [expected])
        for days, expected in [(14, 30), (15, 60), (28, 60), (29, 90)]:
            self.assertEqual(policies.parking({"days": days, "base": 60}), [expected])
        self.assertEqual(policies.gym({"notice": 29, "membership_paid": 80}), [25])
        self.assertEqual(policies.gym({"notice": 30, "membership_paid": 80}), [0])
        self.assertEqual(policies.gym({"notice": 1, "membership_paid": 80, "medical": True}), [0])
        self.assertEqual(policies.energy({"days": 60, "energy_bill": 1000, "support": True}), [0])

    def test_refund_rounding_precedes_voucher_and_threshold(self):
        base = {"receipt": True, "unused": True, "days": 30, "goods_paid": "2.79", "method": "voucher"}
        self.assertEqual(policies.returns(base), [policies.d("2.97")])
        self.assertEqual(policies.returns({**base, "days": 31}), [0])
        self.assertEqual(policies.returns({**base, "goods_paid": "0.99"}), [0])
        self.assertEqual(policies.returns({**base, "goods_paid": "1.00"}), [policies.d("1.10")])

    def test_rail_return_exception_starts_at_120_minutes(self):
        self.assertEqual(policies.rail({"paid": 64, "delay": 119, "return_ticket": True}), [32])
        self.assertEqual(policies.rail({"paid": 64, "delay": 120, "return_ticket": True}), [64])


if __name__ == "__main__":
    unittest.main()
