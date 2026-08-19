from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALUATORS = ROOT / "benchmarks" / "evaluators"
BFCL_ENTRYPOINTS = (
    "test_bfcl.py",
    "test_bfcl_official.py",
    "test_bfcl_claude.py",
    "test_bfcl_claude_extra.py",
)


class BfclRuntimeTests(unittest.TestCase):
    def test_bfcl_has_no_private_checkout_dependency(self) -> None:
        combined = "\n".join(
            (EVALUATORS / name).read_text(encoding="utf-8") for name in BFCL_ENTRYPOINTS
        ).lower()
        self.assertNotIn("skill" + "lens", combined)
        self.assertNotIn("sys.path.insert", combined)
        self.assertIn("load_bfcl_runtime", combined)

    def test_bfcl_extra_is_declared(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('bfcl = ["bfcl-eval==', pyproject)

    def test_help_does_not_require_optional_bfcl_install(self) -> None:
        for name in BFCL_ENTRYPOINTS:
            result = subprocess.run(
                [sys.executable, str(EVALUATORS / name), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=f"{name}: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
