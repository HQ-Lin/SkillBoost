#!/usr/bin/env python3
"""Validate the structure and stage state of a Markdown Repair Brief."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MODULES = [
    "Metadata Header",
    "Baseline Performance Summary",
    "Failure Mode Cluster Analysis",
    "Repair Strategy (Repair Actions)",
    "Repair Action Mapping Table",
    "Anti-Regression Guardrails",
    "Back-Testing Results (Post-evolution)",
    "Execution Plan",
]


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values


def validate(text: str, expected_stage: str) -> dict[str, object]:
    errors: list[str] = []
    metadata = frontmatter(text)
    if metadata.get("artifact") != "skillboost-repair-brief":
        errors.append("frontmatter artifact must be 'skillboost-repair-brief'")
    for key in ("schema_version", "brief_id", "diagnosis_id", "strategy_id", "candidate_id", "status"):
        if not metadata.get(key):
            errors.append(f"frontmatter is missing {key!r}")

    headings = [
        (match.start(), int(match.group(1)), match.group(2).strip())
        for match in re.finditer(r"^##\s+([1-8])\.\s+(.+?)\s*$", text, re.MULTILINE)
    ]
    observed = [title for _, _, title in headings]
    if observed != MODULES:
        errors.append(f"expected the eight ordered modules {MODULES!r}; found {observed!r}")

    status = metadata.get("status")
    allowed = {"draft", "evaluated", "accepted", "rejected"}
    if status and status not in allowed:
        errors.append(f"invalid status {status!r}")
    if expected_stage == "draft" and status != "draft":
        errors.append("draft validation requires status 'draft'")
    if expected_stage == "evaluated" and status not in {"evaluated", "accepted", "rejected"}:
        errors.append("evaluated validation requires evaluated, accepted, or rejected status")

    if len(headings) == 8:
        module_text: dict[int, str] = {}
        for index, (start, number, _) in enumerate(headings):
            end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
            module_text[number] = text[start:end]
        if expected_stage == "evaluated":
            backtest = module_text[7]
            if re.search(r"\b(?:pending|TBD|TODO)\b", backtest, re.IGNORECASE):
                errors.append("evaluated Repair Brief has pending back-testing fields")
            if not re.search(r"\b(?:pass|fail|advance|reject|accepted|rejected)\b", backtest, re.IGNORECASE):
                errors.append("evaluated Repair Brief records no measured gate result")

    return {
        "schema_version": "1.0",
        "valid": not errors,
        "stage": expected_stage,
        "brief_id": metadata.get("brief_id"),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--stage", choices=("draft", "evaluated"), default="draft")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate(args.brief.read_text(encoding="utf-8"), args.stage)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
