"""Regression checks for sampling invariants and offline scoring."""
import copy
import json
import subprocess
import sys
import unittest

from build_items import HERE, build, validate
from run import cosine


class ReviewTests(unittest.TestCase):
    def test_review_cohort(self):
        validate(build())

    def test_domain_concentration_rejected(self):
        items = copy.deepcopy(build())
        items[1]["domain"] = items[0]["domain"]
        with self.assertRaisesRegex(ValueError, "domain"):
            validate(items)

    def test_template_concentration_rejected(self):
        items = copy.deepcopy(build())
        items[1]["template"] = items[0]["template"]
        with self.assertRaisesRegex(ValueError, "template"):
            validate(items)

    def test_unchanged_answer_rejected(self):
        items = copy.deepcopy(build())
        items[0]["query_answer"] = items[0]["source_answer"]
        with self.assertRaisesRegex(ValueError, "different answers"):
            validate(items)

    def test_duplicate_question_rejected(self):
        items = copy.deepcopy(build())
        items[1]["query"] = items[0]["query"]
        with self.assertRaisesRegex(ValueError, "Duplicate question"):
            validate(items)

    def test_cosine(self):
        self.assertAlmostEqual(cosine([1, 0], [0, 1]), 0)
        self.assertAlmostEqual(cosine([2, 0], [3, 0]), 1)
        self.assertAlmostEqual(cosine([2, 0], [-3, 0]), -1)
        for left, right in (([0], [1]), ([1], [1, 2]), ([float("nan")], [1])):
            with self.assertRaises(ValueError):
                cosine(left, right)

    def test_offline_entry_point(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "run.py"), "--dry-run"],
            check=True, capture_output=True, text=True,
        )
        self.assertIn("30 distinct pairs", result.stdout)
        report = json.loads((HERE / "development/dry-run.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "offline_fixture_only")
        self.assertEqual(len(report["rows"]), 30)


if __name__ == "__main__":
    unittest.main()
