"""Synthetic checks for repeat clustering, paired resampling and cascade costing."""

import json
import unittest

from analyse_uncertainty import bootstrap, observations
from common import cost_usd


class UncertaintyTests(unittest.TestCase):
    def row(self, item, repeat, model, amount):
        return {
            "item": item,
            "repeat": repeat,
            "model": model,
            "content": json.dumps({"amount": amount}),
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "finish_reason": "stop",
        }

    def test_three_repeats_remain_one_item_and_agreement_charges_all_three(self):
        items = {"a": {"id": "a", "task": "rules", "gold": {"amount": 10}}}
        runs = {
            "oss-20b": [self.row("a", r, "oss-20b", amount) for r, amount in enumerate([10, 11, 11])],
            "sol": [self.row("a", 0, "sol", 10)],
        }
        ids, vectors = observations(items, runs, ["oss-20b", "sol"])
        self.assertEqual(ids, ["a"])
        self.assertEqual(vectors["oss-20b"][0][0], 1 / 3)
        self.assertEqual(vectors["oss-20b:agreement"][0][0], 1)
        self.assertAlmostEqual(
            vectors["oss-20b:agreement"][0][1], 3 * cost_usd("oss-20b", 100, 10) + cost_usd("sol", 100, 10)
        )
        result = bootstrap(ids, items, vectors, draws=100)
        self.assertEqual(result["n_items"], 1)
        ci = result["policies"]["oss-20b"]["ci95"]["accuracy"]
        self.assertEqual(ci, [1 / 3, 1 / 3])

    def test_consistently_wrong_answers_do_not_escalate(self):
        items = {"a": {"id": "a", "task": "rules", "gold": {"amount": 10}}}
        runs = {"oss-20b": [self.row("a", r, "oss-20b", 11) for r in range(3)], "sol": [self.row("a", 0, "sol", 10)]}
        _, vectors = observations(items, runs, ["oss-20b", "sol"])
        self.assertEqual(vectors["oss-20b:agreement"][0][0], 0)
        self.assertEqual(vectors["oss-20b:agreement"][0][2], 0)

    def test_stratification_and_pairing_keep_fixed_task_mix(self):
        items = {"a": {"task": "invoice"}, "b": {"task": "tool"}}
        vectors = {"sol": [(1, 0.01, 0), (0, 0.01, 0)], "cheap": [(0, 0.001, 0), (1, 0.001, 0)]}
        result = bootstrap(["a", "b"], items, vectors, draws=100)
        self.assertEqual(result["strata"], {"invoice": 1, "tool": 1})
        self.assertEqual(result["policies"]["cheap"]["vs_sol"]["accuracy_difference_pp_ci95"], [0, 0])


if __name__ == "__main__":
    unittest.main()
