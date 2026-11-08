"""A changed frozen input must prevent a measured run."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import freeze
from common import digest


class FreezeTests(unittest.TestCase):
    def test_changed_input_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "items.jsonl"
            source.write_text("original", encoding="utf-8")
            (root / "FREEZE.json").write_text(json.dumps({"sha256": {"items.jsonl": digest(source)}}))
            with patch.object(freeze, "HERE", root), patch.object(freeze, "inputs", return_value=[source]):
                freeze.check()
                source.write_text("changed", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "changed"):
                    freeze.check()

    def test_unpinned_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, "immutable"):
            freeze.create("main")


if __name__ == "__main__":
    unittest.main()
