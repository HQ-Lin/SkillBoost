#!/usr/bin/env python3
"""Prepare deterministic evidence packets for causal skill-failure attribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            task_id = value.get("task_id") if isinstance(value, dict) else None
            if task_id is None:
                raise ValueError(f"{path}:{line_number}: missing task_id")
            records[str(task_id)] = value
    return records


def case_ids(report: dict[str, Any]) -> list[str]:
    values = []
    for key in ("incorrect_cases", "undecided_cases", "fp_cases", "fn_cases", "missing_task_ids"):
        values.extend(report.get(key, []) or [])
    result: list[str] = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("task_id", value.get("id"))
        if value is not None and str(value) not in result:
            result.append(str(value))
    return result


def metric_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report.get("metrics")
    if isinstance(metrics, dict):
        return metrics
    snapshot: dict[str, Any] = {}
    for key in ("accuracy", "pass_rate", "completion_rate", "score", "error_rate"):
        if isinstance(report.get(key), (int, float)):
            snapshot[key] = report[key]
    return snapshot


def correct_ids(report: dict[str, Any]) -> set[str]:
    values = report.get("correct_cases", []) or []
    identifiers: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            value = value.get("task_id", value.get("id"))
        if value is not None:
            identifiers.add(str(value))
    return identifiers


def history_entries(paths: list[Path]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in paths:
        report = load_json(path)
        entries.append(
            {
                "artifact": path.name,
                "run_id": report.get("run_id", path.stem),
                "skill_version": report.get("skill_version", "unknown"),
                "metrics": metric_snapshot(report),
                "correct_ids": correct_ids(report),
            }
        )
    return entries


def brief_summary(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    title = next(
        (line.removeprefix("# ").strip() for line in text.splitlines() if line.startswith("# ")),
        path.stem,
    )
    status = "unknown"
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if match:
        status_match = re.search(r"^status:\s*(.+?)\s*$", match.group(1), re.MULTILINE)
        if status_match:
            status = status_match.group(1).strip(" '\"")
    return f"{path.name}: {title} (status={status})"


def trace_excerpt(path: Path, max_chars: int) -> str:
    if not path.is_file():
        return "[trace missing]"
    try:
        trace = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return f"[trace unreadable: {error}]"
    text = trace.get("result_text", "") if isinstance(trace, dict) else ""
    if not text and isinstance(trace, dict):
        text = json.dumps(trace.get("trace", trace.get("messages", [])), ensure_ascii=False)
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text[-max_chars:] if text else "[trace contains no assistant text]"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("skill", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-trace-chars", type=int, default=2000)
    parser.add_argument(
        "--history-report",
        type=Path,
        action="append",
        default=[],
        help="Earlier evaluation report; repeat in chronological order.",
    )
    parser.add_argument(
        "--prior-brief",
        type=Path,
        action="append",
        default=[],
        help="Earlier Repair Brief; repeat to expose prior attempts.",
    )
    args = parser.parse_args()

    report = load_json(args.report)
    records = load_jsonl(args.results)
    skill_text = args.skill.read_text(encoding="utf-8")
    skill_hash = hashlib.sha256(skill_text.encode("utf-8")).hexdigest()
    headings = [line.strip() for line in skill_text.splitlines() if re.match(r"^#{1,4}\s", line)]
    selected = case_ids(report)
    history = history_entries(args.history_report)
    regressed = {
        task_id: [entry["skill_version"] for entry in history if task_id in entry["correct_ids"]]
        for task_id in selected
    }
    regressed = {task_id: versions for task_id, versions in regressed.items() if versions}

    lines = [
        "# SkillBoost attribution context",
        "",
        "> Deterministic evidence preparation only. No causal labels below are inferred by this script.",
        "",
        "## Run snapshot",
        "",
        f"- Report: `{args.report.name}`",
        f"- Results: `{args.results.name}`",
        f"- Skill: `{args.skill.name}`",
        f"- Skill SHA-256: `{skill_hash}`",
        f"- Failed/undecided cases: {len(selected)}",
        f"- Metrics: `{json.dumps(report.get('metrics', {}), ensure_ascii=False)}`",
        "",
        "## Skill section index",
        "",
        *[f"- {heading}" for heading in headings],
        "",
        "## Version history",
        "",
        *(
            [
                f"- `{entry['skill_version']}` / `{entry['run_id']}` / `{entry['artifact']}`: "
                f"`{json.dumps(entry['metrics'], ensure_ascii=False)}`"
                for entry in history
            ]
            or ["- No earlier reports supplied."]
        ),
        "",
        "## Regression alerts",
        "",
        *(
            [
                f"- Case `{task_id}` was correct in earlier version(s): "
                + ", ".join(f"`{version}`" for version in versions)
                for task_id, versions in sorted(regressed.items())
            ]
            or ["- No current failed/undecided case is known to have been correct in supplied history."]
        ),
        "",
        "## Prior repair artifacts",
        "",
        *([f"- {brief_summary(path)}" for path in args.prior_brief] or ["- No earlier Repair Briefs supplied."]),
        "",
        "## Evidence packets",
    ]

    for task_id in selected:
        record = records.get(task_id, {})
        trace_value = record.get("trace_file")
        trace_path = Path(trace_value) if trace_value else Path("__missing__")
        if trace_value and not trace_path.is_absolute():
            candidates = [args.results.parent / trace_path, args.results.parent.parent / trace_path]
            trace_path = next((path for path in candidates if path.exists()), candidates[0])
        lines.extend(
            [
                "",
                f"### Case `{task_id}`",
                "",
                f"- Status: `{record.get('status', record.get('correct', 'unknown'))}`",
                f"- Ground truth: `{json.dumps(record.get('ground_truth', record.get('gt')), ensure_ascii=False)}`",
                f"- Prediction: `{json.dumps(record.get('prediction', record.get('skill_predict')), ensure_ascii=False)}`",
                f"- Trace: `{Path(str(trace_value)).name if trace_value else 'missing'}`",
                "",
                "**Terminal trace excerpt**",
                "",
                trace_excerpt(trace_path, args.max_trace_chars),
                "",
                "**Analyst fields (complete manually)**",
                "",
                "- Earliest causal error:",
                "- Incumbent skill location:",
                "- Defect class:",
                "- Competing hypothesis:",
            ]
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
