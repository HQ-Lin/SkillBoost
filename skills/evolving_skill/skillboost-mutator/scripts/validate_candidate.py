#!/usr/bin/env python3
"""Validate mutation provenance, scope, references, and complexity budgets."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def text_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.name == "candidate-validation.json":
            continue
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(root).parts):
            try:
                files[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
    return files


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("'\"")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("incumbent", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-changed-lines", type=int, default=200)
    parser.add_argument("--max-growth-ratio", type=float, default=0.25)
    args = parser.parse_args()

    incumbent_files = text_files(args.incumbent)
    candidate_files = text_files(args.candidate)
    errors: list[str] = []
    warnings: list[str] = []
    skill_text = candidate_files.get("SKILL.md", "")
    if not skill_text:
        errors.append("candidate has no readable SKILL.md")
    frontmatter = parse_frontmatter(skill_text)
    for key in ("name", "description"):
        if not frontmatter.get(key):
            errors.append(f"SKILL.md frontmatter is missing {key!r}")

    changed_files: list[dict[str, Any]] = []
    total_added = total_removed = 0
    for relative in sorted(set(incumbent_files) | set(candidate_files)):
        before = incumbent_files.get(relative, "").splitlines()
        after = candidate_files.get(relative, "").splitlines()
        if before == after:
            continue
        diff = list(difflib.ndiff(before, after))
        added = sum(line.startswith("+ ") for line in diff)
        removed = sum(line.startswith("- ") for line in diff)
        total_added += added
        total_removed += removed
        changed_files.append({"path": relative, "added": added, "removed": removed})
    if not changed_files:
        errors.append("candidate is identical to incumbent")
    if total_added + total_removed > args.max_changed_lines:
        errors.append(
            f"changed-line budget exceeded: {total_added + total_removed} > {args.max_changed_lines}"
        )

    incumbent_lines = sum(len(text.splitlines()) for text in incumbent_files.values())
    candidate_lines = sum(len(text.splitlines()) for text in candidate_files.values())
    growth_ratio = (candidate_lines - incumbent_lines) / max(incumbent_lines, 1)
    if growth_ratio > args.max_growth_ratio:
        errors.append(f"growth budget exceeded: {growth_ratio:.4f} > {args.max_growth_ratio:.4f}")

    for target in re.findall(r"\]\((references/[^)#]+)", skill_text):
        if target not in candidate_files:
            errors.append(f"referenced file does not exist: {target}")
    reference_files = {name for name in candidate_files if name.startswith("references/")}
    mounted = set(re.findall(r"\]\((references/[^)#]+)", skill_text))
    for name in sorted(reference_files - mounted):
        warnings.append(f"reference is not mounted from SKILL.md: {name}")
    if re.search(r"^#{1,4}\s+change\s*log", skill_text, re.IGNORECASE | re.MULTILINE):
        errors.append("SKILL.md contains a changelog section; provenance belongs outside the skill")

    addressed_ids: list[str] = []
    if args.brief:
        brief = json.loads(args.brief.read_text(encoding="utf-8"))
        if not isinstance(brief, dict):
            raise ValueError("Repair Brief must be a JSON object")
        clusters = brief.get("failure_clusters", [])
        strategy = brief.get("repair_strategy", {})
        selected = strategy.get("selected_cluster_ids", []) if isinstance(strategy, dict) else []
        addressed_ids = [str(value) for value in selected]
        case_ids = [str(case_id) for cluster in clusters for case_id in cluster.get("case_ids", [])]

        # Compatibility with pre-publication Mutation Brief artifacts.
        if not clusters and "repair_items" in brief:
            items = brief.get("repair_items", [])
            addressed_ids = [
                str(item.get("id"))
                for item in items
                if item.get("disposition") in {"mutate", "decompose"}
            ]
            case_ids = [str(case_id) for item in items for case_id in item.get("case_ids", [])]
        leaked = sorted({case_id for case_id in case_ids if case_id and case_id in skill_text})
        if leaked:
            errors.append(f"candidate embeds source case identifiers: {', '.join(leaked)}")

    report = {
        "schema_version": "1.0",
        "valid": not errors,
        "incumbent": args.incumbent.name,
        "candidate": args.candidate.name,
        "incumbent_sha256": hashlib.sha256(
            incumbent_files.get("SKILL.md", "").encode("utf-8")
        ).hexdigest(),
        "candidate_sha256": hashlib.sha256(skill_text.encode("utf-8")).hexdigest(),
        "addressable_repair_ids": addressed_ids,
        "changed_files": changed_files,
        "added_lines": total_added,
        "removed_lines": total_removed,
        "growth_ratio": growth_ratio,
        "errors": errors,
        "warnings": warnings,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    output = args.output or args.candidate / "candidate-validation.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
