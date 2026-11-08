"""Regression tests for full-cohort labels, retrieval scores and the guard."""
import copy
import unittest

from common import guard_passes, guard_tokens
from corpus import cache_entries, full_items, validate_full


class FullTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = full_items()
        cls.cache = cache_entries(cls.items)

    def test_full_counts_and_answer_key(self):
        validate_full(self.items)
        self.assertEqual(len(self.cache), 1000)
        self.assertEqual(len({row["text"] for row in self.cache}), 1000)
        for item in self.items:
            expected = [row["id"] for row in self.cache if row["answer"] == item["query_answer"]]
            self.assertEqual(item["acceptable_ids"], expected)
            if item["type"] == "paraphrase":
                self.assertTrue(expected)

    def test_domain_cap_rejected(self):
        items = copy.deepcopy(self.items)
        for item in items:
            if item["type"] == "paraphrase":
                item["domain"] = "shop"
        with self.assertRaisesRegex(ValueError, "domain"):
            validate_full(items)

    def test_guard_literals(self):
        self.assertFalse(guard_passes("order A-01", "order A-10"))
        self.assertFalse(guard_passes("day 14", "day 15"))
        self.assertFalse(guard_passes("on 12 November", "on 13 November"))
        self.assertFalse(guard_passes("yes", "not yes"))
        self.assertFalse(guard_passes("ID 001", "ID 1"))
        self.assertFalse(guard_passes("1 and 1", "1"))
        self.assertTrue(guard_passes("I can't use 5", "5 I can’t use"))
        self.assertTrue(guard_passes("5 divided by 2", "2 divided by 5"))
        self.assertTrue(guard_passes("my account", "your account"))
        self.assertEqual(guard_tokens("on 2026-11-08")["2026-11-08"], 1)

    def test_cache_has_no_verbatim_queries(self):
        stored = {row["text"] for row in self.cache}
        self.assertFalse(stored.intersection(item["query"] for item in self.items))


if __name__ == "__main__":
    unittest.main()
