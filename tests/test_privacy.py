from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yaml", ".yml", ".sh"}


class PrivacyTests(unittest.TestCase):
    def test_no_personal_paths_emails_or_secret_literals(self) -> None:
        forbidden = [
            re.compile(re.escape("/" + "Users" + "/")),
            re.compile(re.escape("/" + "home" + "/")),
            re.compile(r"[A-Za-z]:\\\\Users\\\\", re.IGNORECASE),
            re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
            re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
            re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
            re.compile(r"xox[baprs]-[A-Za-z0-9-]{12,}"),
            re.compile(r"BEGIN (?:RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY"),
        ]
        failures: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in forbidden):
                failures.append(str(path.relative_to(ROOT)))
        self.assertEqual(failures, [])

    def test_credentials_are_not_accepted_on_command_line(self) -> None:
        option = "--" + "api" + "-key"
        offenders = []
        for path in ROOT.rglob("*.py"):
            if option in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_release_contains_no_identity_metadata_or_local_artifacts(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn("authors =", pyproject)
        forbidden_names = {".DS_Store", ".env", "credentials.json", "secrets.json"}
        offenders = [
            str(path.relative_to(ROOT))
            for path in ROOT.rglob("*")
            if path.is_file() and path.name in forbidden_names
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
