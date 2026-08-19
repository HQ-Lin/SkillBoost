#!/usr/bin/env python3
"""Normalize exact-match task traces into SkillBoost evaluation artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            records.append(value)
    return records


def extract_result_text(trace: dict[str, Any]) -> str:
    if isinstance(trace.get("result_text"), str):
        return trace["result_text"]
    messages = trace.get("trace", trace.get("messages", []))
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [block.get("text", "") for block in content if isinstance(block, dict)]
            if any(parts):
                return "\n".join(parts)
    return ""


def extract_tool_calls(trace: dict[str, Any]) -> list[str]:
    calls: list[str] = []
    messages = trace.get("trace", trace.get("messages", []))
    if not isinstance(messages, list):
        return calls
    for message in messages:
        if not isinstance(message, dict):
            continue
        for call in message.get("tool_calls", []) or []:
            if not isinstance(call, dict):
                continue
            function = call.get("function", {})
            name = function.get("name") if isinstance(function, dict) else None
            name = name or call.get("name")
            if name:
                calls.append(str(name))
    return calls


def parse_json_object(text: str) -> dict[str, Any] | None:
    candidates = [text.strip()]
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def normalize(value: Any, mode: str) -> Any:
    if mode == "json":
        return value
    text = str(value).strip()
    if mode == "lower":
        return " ".join(text.casefold().split())
    if mode == "number":
        try:
            number = float(text.replace(",", ""))
            return number if math.isfinite(number) else text
        except ValueError:
            return text
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--skill-version", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--id-field", default="task_id")
    parser.add_argument("--label-field", default="answer")
    parser.add_argument("--prediction-field", default="answer")
    parser.add_argument("--group-field", default="")
    parser.add_argument("--normalizer", choices=("exact", "lower", "number", "json"), default="exact")
    parser.add_argument("--parser-revision", default="generic-json-v1")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    traces_dir = args.run_dir / "traces"
    if not traces_dir.is_dir():
        raise FileNotFoundError(f"missing traces directory: {traces_dir}")
    cases = load_jsonl(args.data)
    identifiers = [str(case.get(args.id_field, "")) for case in cases]
    if "" in identifiers or len(set(identifiers)) != len(identifiers):
        raise ValueError(f"{args.id_field!r} must be present and unique")

    records: list[dict[str, Any]] = []
    for case, task_id in zip(cases, identifiers):
        trace_path = traces_dir / f"trace_{task_id}.json"
        record: dict[str, Any] = {
            "task_id": task_id,
            "ground_truth": case.get(args.label_field),
            "prediction": None,
            "status": "missing",
            "trace_file": f"traces/trace_{task_id}.json" if trace_path.exists() else None,
            "parser_revision": args.parser_revision,
            "tool_calls": [],
            "result_text": "",
        }
        if args.group_field:
            record["group"] = str(case.get(args.group_field, "unknown"))
        if trace_path.exists():
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            result_text = extract_result_text(trace)
            record["result_text"] = result_text
            record["tool_calls"] = extract_tool_calls(trace)
            parsed = parse_json_object(result_text)
            if parsed is None or args.prediction_field not in parsed:
                record["status"] = "unknown"
            else:
                prediction = parsed[args.prediction_field]
                record["prediction"] = prediction
                record["status"] = (
                    "correct"
                    if normalize(prediction, args.normalizer)
                    == normalize(case.get(args.label_field), args.normalizer)
                    else "incorrect"
                )
        records.append(record)

    counts = Counter(record["status"] for record in records)
    total = len(records)
    decided = counts["correct"] + counts["incorrect"]
    slice_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        if "group" in record:
            slice_counts[record["group"]][record["status"]] += 1
    slice_metrics = {}
    for group, group_counts in sorted(slice_counts.items()):
        group_total = sum(group_counts.values())
        slice_metrics[group] = {
            "accuracy": group_counts["correct"] / group_total if group_total else 0.0,
            "completion_rate": (
                group_counts["correct"] + group_counts["incorrect"]
            ) / group_total if group_total else 0.0,
        }

    created_at = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "run_id": args.run_dir.name,
        "skill_version": args.skill_version,
        "dataset_id": args.dataset_id,
        "primary_metric": "accuracy",
        "metric_direction": "maximize",
        "metrics": {
            "accuracy": counts["correct"] / total if total else 0.0,
            "decided_accuracy": counts["correct"] / decided if decided else 0.0,
            "completion_rate": decided / total if total else 0.0,
        },
        "total": total,
        "decided": decided,
        "missing": counts["missing"],
        "unknown": counts["unknown"],
        "correct_cases": [r["task_id"] for r in records if r["status"] == "correct"],
        "incorrect_cases": [r["task_id"] for r in records if r["status"] == "incorrect"],
        "undecided_cases": [r["task_id"] for r in records if r["status"] in {"missing", "unknown"}],
        "slice_metrics": slice_metrics,
        "config": {
            "id_field": args.id_field,
            "label_field": args.label_field,
            "prediction_field": args.prediction_field,
            "normalizer": args.normalizer,
            "parser_revision": args.parser_revision,
        },
        "created_at": created_at.isoformat(),
    }

    output_dir = args.output_dir or args.run_dir / "evals"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    results_path = output_dir / f"results_{stamp}.jsonl"
    report_path = output_dir / f"report_{stamp}.json"
    with results_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"results: {results_path}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
