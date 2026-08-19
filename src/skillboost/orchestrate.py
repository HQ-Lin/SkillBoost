#!/usr/bin/env python3
"""Two-stage, regression-aware candidate selection for SkillBoost."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import SelectionPolicy, candidate_assessment, extract_failure_ids, metric_value


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def find_latest_report(output_base: Path) -> Path | None:
    candidates = list(output_base.glob("*_run_*/evals/report_*.json"))
    candidates.extend(output_base.glob("evals/report_*.json"))
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def portable_path(path: Path, project_root: Path) -> str:
    """Serialize a path without leaking a workstation-specific absolute prefix."""
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return path.name


def write_promotion_artifacts(
    destination: Path,
    winner: dict[str, Any],
    record: dict[str, Any],
) -> tuple[Path, Path]:
    """Write immutable version provenance and an external round changelog."""
    skill_path = destination / "SKILL.md"
    skill_sha256 = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    candidate_record = next(
        item for item in record["candidates"] if item["candidate"] == winner["candidate"]
    )
    manifest = {
        "schema_version": "1.0",
        "version_id": destination.name,
        "round_id": record["round_id"],
        "parent": record["incumbent"],
        "candidate": winner["candidate"],
        "brief_id": candidate_record.get("brief_id", record["brief_id"]),
        "skill_sha256": skill_sha256,
        "evaluation_report": candidate_record["report_path"],
        "decision": "promoted",
        "created_at": record["created_at"],
    }
    manifest_path = destination / "skillboost-version.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changelog_dir = destination.parent / "changelogs"
    changelog_dir.mkdir(parents=True, exist_ok=True)
    changelog_path = changelog_dir / f"changelog_{record['round_id']}.md"
    if changelog_path.exists():
        raise FileExistsError(f"changelog already exists: {changelog_path}")
    assessment = candidate_record["assessment"]
    lines = [
        f"# Changelog: {destination.name}",
        "",
        f"- Round: `{record['round_id']}`",
        f"- Parent evaluation: `{record['incumbent']}`",
        f"- Promoted candidate: `{winner['candidate']}`",
        f"- Repair Brief: `{candidate_record.get('brief_id', record['brief_id'])}`",
        f"- Skill SHA-256: `{skill_sha256}`",
        f"- Full evaluation: `{candidate_record['report_path']}`",
        "",
        "## Acceptance summary",
        "",
        f"- Primary improvement: `{assessment.get('improvement')}`",
        f"- Completion: `{assessment.get('completion_rate')}`",
        f"- Case regression rate: `{assessment.get('case_regression_rate')}`",
        f"- Fix rate: `{assessment.get('fix_rate')}`",
        f"- Slice regressions: `{json.dumps(assessment.get('slice_regressions', {}), ensure_ascii=False)}`",
        "- Decision: promoted after all predeclared full-set gates passed.",
    ]
    changelog_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path, changelog_path


def run_evaluation(
    eval_script: Path,
    data: Path,
    skill_dir: Path,
    output_base: Path,
    concurrency: int,
    concurrency_arg: str,
    filter_ids: list[str] | None,
    extra_args: list[str],
) -> tuple[dict[str, Any], Path]:
    output_base.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(eval_script),
        "--data",
        str(data),
        "--skill",
        str(skill_dir),
        "--output-base",
        str(output_base),
        concurrency_arg,
        str(concurrency),
        *extra_args,
    ]
    if filter_ids:
        command.extend(["--filter-ids", *filter_ids])

    mode = "directed" if filter_ids else "full"
    print(f"[skillboost] {mode} evaluation: {skill_dir.name}")
    subprocess.run(command, check=True)
    report_path = find_latest_report(output_base)
    if report_path is None:
        raise RuntimeError(f"evaluation produced no report under {output_base}")
    return load_json(report_path), report_path


def _candidate_score(report: dict[str, Any], policy: SelectionPolicy) -> float:
    value = metric_value(report, policy.metric_key)
    if value is None:
        return float("-inf")
    return value if policy.metric_direction == "maximize" else -value


def _validate_inputs(args: argparse.Namespace, project_root: Path) -> tuple[Path, Path, Path, list[Path]]:
    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else project_root / path

    eval_script = resolve(args.eval_script)
    data = resolve(args.data)
    baseline_report = resolve(args.baseline_report)
    candidates = [resolve(value) for value in args.candidates]
    for path in (eval_script, data, baseline_report):
        if not path.exists():
            raise FileNotFoundError(path)
    for candidate in candidates:
        target = candidate / args.candidate_subdir if args.candidate_subdir else candidate
        if not (target / "SKILL.md").is_file():
            raise FileNotFoundError(f"candidate has no SKILL.md: {target}")
    if not 1 <= args.topk <= len(candidates):
        raise ValueError("--topk must be between 1 and the number of candidates")
    return eval_script, data, baseline_report, candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Screen skill mutations on incumbent failures, then apply full-set promotion gates."
    )
    parser.add_argument("--eval-script", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--candidates", nargs="+", required=True)
    parser.add_argument("--output-base", required=True)
    parser.add_argument("--topk", type=int, default=2)
    parser.add_argument("--max-concurrent", type=int, default=20)
    parser.add_argument("--concurrency-arg", default="--max-concurrent")
    parser.add_argument("--eval-extra-arg", action="append", default=[])
    parser.add_argument("--eval-extra-args", default="", help=argparse.SUPPRESS)
    parser.add_argument("--candidate-subdir", default="")
    parser.add_argument("--fail-ids-key", default="")
    parser.add_argument("--extra-targeted-id", action="append", default=[])
    parser.add_argument("--extra-targeted-ids", nargs="*", default=[], help=argparse.SUPPRESS)
    parser.add_argument("--metric-key", default="accuracy")
    parser.add_argument("--metric-direction", choices=("maximize", "minimize"), default="maximize")
    parser.add_argument("--group-key", default="per_group")
    parser.add_argument("--min-improvement", type=float, default=0.0)
    parser.add_argument("--max-regression", type=float, default=None)
    parser.add_argument("--max-slice-regression", type=float, default=0.0)
    parser.add_argument("--min-completion", type=float, default=0.0)
    parser.add_argument("--round-id", default="")
    parser.add_argument("--brief-id", default="unknown")
    parser.add_argument(
        "--candidate-brief",
        action="append",
        default=[],
        metavar="CANDIDATE=BRIEF_ID",
        help="Associate a candidate directory name with its Repair Brief ID; repeat per candidate.",
    )
    parser.add_argument("--baseline-version", default="", help=argparse.SUPPRESS)
    parser.add_argument("--target-version", default="", help=argparse.SUPPRESS)
    parser.add_argument("--task-line", default="", help=argparse.SUPPRESS)
    parser.add_argument("--correct-key", default="", help=argparse.SUPPRESS)
    parser.add_argument("--promote-to", default="", help="Copy the winner here only after all gates pass.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(__file__).resolve().parents[2]
    eval_script, data, baseline_path, candidate_dirs = _validate_inputs(args, project_root)
    output_base = Path(args.output_base)
    if not output_base.is_absolute():
        output_base = project_root / output_base

    baseline = load_json(baseline_path)
    brief_by_candidate: dict[str, str] = {}
    for assignment in args.candidate_brief:
        if "=" not in assignment:
            raise ValueError("--candidate-brief must use CANDIDATE=BRIEF_ID")
        candidate_name, brief_id = assignment.split("=", 1)
        if not candidate_name or not brief_id or candidate_name in brief_by_candidate:
            raise ValueError(f"invalid or duplicate --candidate-brief assignment: {assignment!r}")
        brief_by_candidate[candidate_name] = brief_id
    unknown_candidates = set(brief_by_candidate) - {path.name for path in candidate_dirs}
    if unknown_candidates:
        raise ValueError(f"Repair Brief mapped to unknown candidates: {sorted(unknown_candidates)}")
    targeted_ids = extract_failure_ids(baseline, args.fail_ids_key or None)
    targeted_ids = list(
        dict.fromkeys(
            [*targeted_ids, *map(str, args.extra_targeted_id), *map(str, args.extra_targeted_ids)]
        )
    )
    if not targeted_ids:
        raise ValueError("the baseline report contains no failed or undecided case identifiers")

    policy = SelectionPolicy(
        metric_key=args.metric_key,
        metric_direction=args.metric_direction,
        min_improvement=args.min_improvement,
        max_case_regression=args.max_regression,
        max_slice_regression=args.max_slice_regression,
        min_completion=args.min_completion,
        group_key=args.group_key,
    )
    eval_extra_args = [*args.eval_extra_arg, *shlex.split(args.eval_extra_args)]

    phase_a: list[dict[str, Any]] = []
    for candidate_dir in candidate_dirs:
        skill_dir = candidate_dir / args.candidate_subdir if args.candidate_subdir else candidate_dir
        report, path = run_evaluation(
            eval_script,
            data,
            skill_dir,
            output_base / f"{candidate_dir.name}_directed",
            args.max_concurrent,
            args.concurrency_arg,
            targeted_ids,
            eval_extra_args,
        )
        phase_a.append(
            {
                "candidate": candidate_dir.name,
                "candidate_dir": str(candidate_dir),
                "report": report,
                "report_path": str(path),
                "screen_score": _candidate_score(report, policy),
                "brief_id": brief_by_candidate.get(candidate_dir.name, args.brief_id),
            }
        )
    phase_a.sort(key=lambda item: item["screen_score"], reverse=True)

    phase_b: list[dict[str, Any]] = []
    for screened in phase_a[: args.topk]:
        candidate_dir = Path(screened["candidate_dir"])
        skill_dir = candidate_dir / args.candidate_subdir if args.candidate_subdir else candidate_dir
        report, path = run_evaluation(
            eval_script,
            data,
            skill_dir,
            output_base / f"{candidate_dir.name}_full",
            args.max_concurrent,
            args.concurrency_arg,
            None,
            eval_extra_args,
        )
        phase_b.append(
            {
                "candidate": candidate_dir.name,
                "candidate_dir": str(candidate_dir),
                "_candidate_path": candidate_dir,
                "report_path": str(path),
                "assessment": candidate_assessment(baseline, report, policy),
                "brief_id": screened["brief_id"],
            }
        )

    eligible = [item for item in phase_b if item["assessment"]["eligible"]]
    eligible.sort(
        key=lambda item: item["assessment"]["improvement"]
        if item["assessment"]["improvement"] is not None
        else float("-inf"),
        reverse=True,
    )
    winner = eligible[0] if eligible else None

    record = {
        "schema_version": "1.0",
        "round_id": args.round_id or datetime.now(timezone.utc).strftime("round-%Y%m%dT%H%M%SZ"),
        "incumbent": portable_path(baseline_path, project_root),
        "brief_id": args.brief_id,
        "brief_ids": {
            candidate_dir.name: brief_by_candidate.get(candidate_dir.name, args.brief_id)
            for candidate_dir in candidate_dirs
        },
        "gates": {
            "metric_key": policy.metric_key,
            "metric_direction": policy.metric_direction,
            "min_improvement": policy.min_improvement,
            "max_case_regression": policy.max_case_regression,
            "max_slice_regression": policy.max_slice_regression,
            "min_completion": policy.min_completion,
        },
        "directed_case_ids": targeted_ids,
        "phase_a": [
            {
                "candidate": item["candidate"],
                "candidate_dir": portable_path(Path(item["candidate_dir"]), project_root),
                "report_path": portable_path(Path(item["report_path"]), project_root),
                "screen_score": item["screen_score"],
                "brief_id": item["brief_id"],
            }
            for item in phase_a
        ],
        "candidates": [
            {
                "candidate": item["candidate"],
                "candidate_dir": portable_path(item["_candidate_path"], project_root),
                "report_path": portable_path(Path(item["report_path"]), project_root),
                "assessment": item["assessment"],
                "brief_id": item["brief_id"],
            }
            for item in phase_b
        ],
        "decision": {
            "status": "promoted" if winner else "rejected",
            "winner": winner["candidate"] if winner else None,
            "reasons": (
                ["winner passed all predeclared full-set promotion gates"]
                if winner
                else ["no candidate passed all full-set promotion gates"]
            ),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    output_base.mkdir(parents=True, exist_ok=True)
    record_path = output_base / "selection-record.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[skillboost] selection record: {record_path}")

    if args.promote_to and winner:
        destination = Path(args.promote_to)
        if not destination.is_absolute():
            destination = project_root / destination
        if destination.exists():
            raise FileExistsError(f"promotion destination already exists: {destination}")
        shutil.copytree(winner["_candidate_path"], destination)
        manifest_path, changelog_path = write_promotion_artifacts(destination, winner, record)
        print(f"[skillboost] promoted {winner['candidate']} -> {destination}")
        print(f"[skillboost] version manifest: {manifest_path}")
        print(f"[skillboost] changelog: {changelog_path}")

    return 0 if winner else 2


if __name__ == "__main__":
    raise SystemExit(main())
