import unittest

from bm25 import BM25, rank
from chunking import chunk, configs, fixed, paragraph_aware
from common import DATA, QUESTIONS, read_jsonl
from scoring import contains, outcome

TEXT = "a b c d e f g h i j"


class Chunking(unittest.TestCase):
    def test_fixed_no_overlap_covers_all_words_once(self):
        ch = fixed(TEXT, 4)
        self.assertEqual([TEXT[s:e] for s, e in ch], ["a b c d", "e f g h", "i j"])

    def test_fixed_overlap(self):
        ch = fixed(TEXT, 4, 2)
        self.assertEqual([TEXT[s:e] for s, e in ch], ["a b c d", "c d e f", "e f g h", "g h i j"])

    def test_bad_overlap(self):
        with self.assertRaises(ValueError):
            fixed(TEXT, 4, 4)

    def test_paragraph_aware_merges_and_splits(self):
        t = "one two\n\nthree four\n\n" + " ".join(f"w{i}" for i in range(7))
        ch = paragraph_aware(t, 4)
        self.assertEqual([t[s:e] for s, e in ch], ["one two\n\nthree four", "w0 w1 w2 w3", "w4 w5 w6"])

    def test_configs(self):
        self.assertEqual(len(configs()), 12)


class Scoring(unittest.TestCase):
    def test_outcomes(self):
        chunks = [(0, 10), (10, 20), (20, 30)]
        self.assertEqual(outcome([(0, 10)], chunks, [[2, 8]]), "found")
        self.assertEqual(outcome([(0, 10)], chunks, [[8, 12]]), "partial")
        self.assertEqual(outcome([(20, 30)], chunks, [[8, 12]]), "cut")
        self.assertEqual(outcome([(20, 30)], chunks, [[2, 8]]), "missed")
        self.assertTrue(contains((0, 10), [0, 10]))

    def test_split_clause_found_when_both_halves_retrieved(self):
        text = "aaaa bbbb cccc dddd"
        chunks = [(0, 9), (10, 19)]
        self.assertEqual(outcome([(10, 19), (0, 9)], chunks, [[5, 14]], text), "found")
        self.assertEqual(outcome([(0, 9)], chunks, [[5, 14]], text), "partial")


class Bm25(unittest.TestCase):
    def test_rank_prefers_matching_chunk(self):
        idx = BM25(["the governing law is delaware", "payment terms net thirty", "notices by mail"])
        self.assertEqual(rank(idx.scores("which law governs"))[0], 0)


class Data(unittest.TestCase):
    def test_items_match_contract_text(self):
        contracts = {c["contract_id"]: c["text"] for c in read_jsonl(DATA / "contracts.jsonl")}
        items = read_jsonl(DATA / "items.jsonl")
        self.assertEqual(len(contracts), 60)
        self.assertEqual(len(items), 334)
        for it in items:
            self.assertIn(it["category"], QUESTIONS)
            for s, e in it["gold_spans"]:
                self.assertTrue(contracts[it["contract_id"]][s:e].strip())

    def test_every_word_is_in_some_chunk(self):
        text = read_jsonl(DATA / "contracts.jsonl")[0]["text"]
        n = len(text.split())
        for name, cfg in configs().items():
            ch = chunk(text, cfg)
            covered = sum(len(text[s:e].split()) for s, e in ch)
            self.assertGreaterEqual(covered, n, name)


class Improve(unittest.TestCase):
    def test_rrf_merges(self):
        from pc_methods import rrf
        self.assertEqual(rrf([0, 1, 2], [2, 0, 1])[0], 0)

    def test_headings_inline_and_path(self):
        from improve import header_for, headings
        t = "10. Term and Termination.\n10.1 Renewal. This renews yearly.\nMore text"
        h = headings(t)
        self.assertEqual([x[1] for x in h], ["10 Term and Termination", "10 Term and Termination > 10.1 Renewal"])
        self.assertEqual(header_for(h, len(t) - 3), "10 Term and Termination > 10.1 Renewal")

    def test_split_is_20_40(self):
        from improve import split_contracts
        dev, test = split_contracts([f"c{i:02d}" for i in range(60)])
        self.assertEqual((len(dev), len(test)), (20, 40))
        self.assertFalse(dev & test)


if __name__ == "__main__":
    unittest.main()
