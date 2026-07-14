"""Contract tests for the private machine-tool v3 formal boundary."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "breeze" / "scripts" / "mt_private_v3_formal.py"
SPEC = importlib.util.spec_from_file_location("mt_private_v3_formal", SCRIPT)
formal = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = formal
SPEC.loader.exec_module(formal)


class PrivateMachineToolV3FormalTests(unittest.TestCase):
    def test_frozen_formal_contract(self) -> None:
        self.assertEqual(formal.CANDIDATE_METHOD, "s_c_llm")
        self.assertEqual(formal.FORMAL_TRAIN_FILE_IDS, ("1", "2", "4", "5", "10"))
        self.assertEqual(formal.FORMAL_TEST_FILE_IDS, ("7", "8"))
        self.assertEqual(formal.FORMAL_SEEDS, tuple(range(40)))
        self.assertEqual(formal.N_SYN_BY_N_REAL, {10: 10, 25: 20, 50: 20})

    def test_formal_loader_rejects_files_outside_its_declared_split(self) -> None:
        with self.assertRaises(RuntimeError):
            formal._find_csv("1", "8", formal.FORMAL_TRAIN_FILE_IDS)

    def test_formal_access_requires_a_preregistration_lock_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_prereg, old_lock = formal.PREREG_PATH, formal.LOCK_PATH
            formal.PREREG_PATH = Path(directory) / "missing.md"
            formal.LOCK_PATH = Path(directory) / "missing.json"
            with self.assertRaises(RuntimeError):
                formal.validate_preregistration()
            formal.PREREG_PATH, formal.LOCK_PATH = old_prereg, old_lock


if __name__ == "__main__":
    unittest.main()
