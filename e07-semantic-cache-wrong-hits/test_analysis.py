"""Tests of paired resampling and corrupted saved embeddings."""
import unittest

from analyse_uncertainty import bootstrap


class BootstrapTests(unittest.TestCase):
    def test_identical_models_have_zero_paired_difference(self):
        rows = [
            {"id": "a", "group": "paraphrase", "family": "f1", "pair_cosine": 0.9,
             "pair_correct": True, "pair_guard": True, "lookup_cosine": 0.9,
             "lookup_correct": True, "lookup_guard": True},
            {"id": "b", "group": "entity_id", "family": "f2", "pair_cosine": 0.95,
             "pair_correct": False, "pair_guard": False, "lookup_cosine": 0.95,
             "lookup_correct": False, "lookup_guard": False},
        ]
        result = bootstrap({"left": {"rows": rows}, "right": {"rows": rows}}, repeats=20)
        for estimates in result.values():
            self.assertTrue(all(interval == [0, 0] for interval in estimates["left-minus-right"]))
        self.assertEqual(result["pair/near_miss/wrong"]["left"][0], [1, 1])
        self.assertEqual(result["pair_guarded/near_miss/wrong"]["left"][0], [0, 0])

    def test_misaligned_models_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "same ordered"):
            bootstrap({"a": {"rows": [{"id": "x"}]}, "b": {"rows": [{"id": "y"}]}}, repeats=5)


if __name__ == "__main__":
    unittest.main()
