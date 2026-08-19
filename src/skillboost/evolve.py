#!/usr/bin/env python3
"""Prepare a SkillBoost round and run its analyzer/mutator with Claude Code."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _inside_project(project_root: Path, value: str, *, kind: str) -> Path:
    path = Path(value)
    path = (path if path.is_absolute() else project_root / path).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as error:
        raise ValueError(f"{kind} must be inside the project workspace: {value}") from error
    if kind == "directory" and not path.is_dir():
        raise FileNotFoundError(path)
    if kind == "file" and not path.is_file():
        raise FileNotFoundError(path)
    return path


def _portable(path: Path, project_root: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_prompt(
    *,
    round_id: str,
    candidate_count: int,
    incumbent: str,
    report: str,
    results: str,
    context: str,
    round_dir: str,
) -> str:
    candidate_lines = "\n".join(
        f"- candidate-{index}: `{round_dir}/candidates/candidate-{index}/`; "
        f"brief ID `brief-{round_id}-{index}`; briefs "
        f"`{round_dir}/briefs/repair-brief-{index}.md` and `.json`"
        for index in range(1, candidate_count + 1)
    )
    return f"""# SkillBoost evolution round: {round_id}

You are the evolution model, not the benchmark task model. The frozen task model has already
executed the incumbent; use its traces and evaluation artifacts as evidence. Do not call a model
provider, rerun benchmark cases, or insert task-specific answers into the skill.

## Inputs

- incumbent skill: `{incumbent}`
- baseline report: `{report}`
- baseline case records: `{results}`
- prepared attribution context: `{context}`
- round workspace: `{round_dir}`

## Required procedure

1. Read `skills/evolving_skill/skillboost-analyzer/SKILL.md` completely. Read the diagnosis
   template and attribution guide it routes to. Inspect the prepared context, incumbent, baseline
   report, case records, and referenced raw traces.
2. Perform evidence-grounded causal attribution. Write one shared diagnosis to
   `{round_dir}/diagnosis.md` and `{round_dir}/diagnosis.json`. The JSON must conform to
   `schemas/diagnosis.schema.json`. Do not edit the incumbent.
3. Read `skills/evolving_skill/skillboost-mutator/SKILL.md` completely and read the repair
   strategy, Repair Brief, mutation-operator, and promotion-policy references it routes to.
4. Construct {candidate_count} materially different strategies from the same immutable diagnosis.
   Each candidate directory is already an exact copy of the incumbent; edit only its local files.
5. For every candidate, write a draft eight-module Repair Brief in both Markdown and JSON. Modules
   1-6 must be complete, module 7 must remain pending, and module 8 must describe the planned
   evaluation. The JSON must conform to `schemas/repair-brief.schema.json`.
6. Keep edits bounded, generic, and causally tied to diagnosed clusters. Preserve all unrelated
   incumbent behavior and mounted references. Do not write benchmark case IDs, gold answers, local
   machine paths, credentials, or provider-specific instructions into candidate skills.
7. Finish only after every required output exists. Do not evaluate or promote candidates; the
   deterministic orchestrator performs that later with the frozen benchmark evaluator.

## Candidate outputs

{candidate_lines}

Return a concise summary listing the diagnosis ID, each candidate's strategy thesis, and all files
created or changed.
"""


def _prepare_context(
    *,
    project_root: Path,
    report: Path,
    results: Path,
    incumbent: Path,
    output: Path,
    history_reports: list[Path],
    prior_briefs: list[Path],
) -> None:
    script = (
        project_root
        / "skills/evolving_skill/skillboost-analyzer/scripts/prepare_context.py"
    )
    command = [
        sys.executable,
        str(script),
        str(report),
        str(results),
        str(incumbent / "SKILL.md"),
        "--output",
        str(output),
    ]
    for path in history_reports:
        command.extend(["--history-report", str(path)])
    for path in prior_briefs:
        command.extend(["--prior-brief", str(path)])
    subprocess.run(command, cwd=project_root, check=True)


def _validate_outputs(
    *,
    project_root: Path,
    round_dir: Path,
    incumbent: Path,
    candidate_count: int,
) -> list[dict[str, str]]:
    diagnosis_md = round_dir / "diagnosis.md"
    diagnosis_json = round_dir / "diagnosis.json"
    for path in (diagnosis_md, diagnosis_json):
        if not path.is_file():
            raise FileNotFoundError(f"evolution model did not create {path}")
    diagnosis = json.loads(diagnosis_json.read_text(encoding="utf-8"))
    diagnosis_id = str(diagnosis.get("diagnosis_id", ""))
    if not diagnosis_id:
        raise ValueError("diagnosis.json has no diagnosis_id")

    brief_validator = (
        project_root
        / "skills/evolving_skill/skillboost-mutator/scripts/validate_repair_brief.py"
    )
    candidate_validator = (
        project_root
        / "skills/evolving_skill/skillboost-mutator/scripts/validate_candidate.py"
    )
    records: list[dict[str, str]] = []
    for index in range(1, candidate_count + 1):
        candidate_id = f"candidate-{index}"
        candidate = round_dir / "candidates" / candidate_id
        brief_md = round_dir / "briefs" / f"repair-brief-{index}.md"
        brief_json = round_dir / "briefs" / f"repair-brief-{index}.json"
        for path in (candidate / "SKILL.md", brief_md, brief_json):
            if not path.is_file():
                raise FileNotFoundError(f"evolution model did not create {path}")
        brief = json.loads(brief_json.read_text(encoding="utf-8"))
        if brief.get("candidate_id") != candidate_id:
            raise ValueError(f"{brief_json} candidate_id does not match {candidate_id}")
        if brief.get("diagnosis_id") != diagnosis_id:
            raise ValueError(f"{brief_json} does not reference {diagnosis_id}")
        if brief.get("status") != "draft":
            raise ValueError(f"{brief_json} must remain draft before evaluation")
        subprocess.run(
            [sys.executable, str(brief_validator), str(brief_md), "--stage", "draft"],
            cwd=project_root,
            check=True,
        )
        subprocess.run(
            [sys.executable, str(candidate_validator), str(incumbent), str(candidate)],
            cwd=project_root,
            check=True,
        )
        records.append(
            {
                "candidate_id": candidate_id,
                "candidate_dir": _portable(candidate, project_root),
                "brief_id": str(brief.get("brief_id", "")),
                "brief_markdown": _portable(brief_md, project_root),
                "brief_json": _portable(brief_json, project_root),
            }
        )
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SkillBoost analysis and mutation after a baseline evaluation."
    )
    parser.add_argument("--incumbent", required=True, help="Incumbent task-skill directory.")
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--baseline-results", required=True)
    parser.add_argument("--round-dir", required=True, help="New immutable round workspace.")
    parser.add_argument("--round-id", default="")
    parser.add_argument("--candidate-count", type=int, default=4)
    parser.add_argument("--history-report", action="append", default=[])
    parser.add_argument("--prior-brief", action="append", default=[])
    parser.add_argument(
        "--runner",
        choices=("claude-code", "prepare-only", "validate-only"),
        default="claude-code",
    )
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--model", default="")
    parser.add_argument("--max-turns", type=int, default=80)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.candidate_count < 1:
        raise ValueError("--candidate-count must be positive")
    if args.max_turns < 1:
        raise ValueError("--max-turns must be positive")

    project_root = Path.cwd().resolve()
    if not (project_root / "skills/evolving_skill").is_dir():
        raise RuntimeError("run skillboost-evolve from the SkillBoost repository root")
    incumbent = _inside_project(project_root, args.incumbent, kind="directory")
    if not (incumbent / "SKILL.md").is_file():
        raise FileNotFoundError(f"incumbent has no SKILL.md: {incumbent}")
    report = _inside_project(project_root, args.baseline_report, kind="file")
    results = _inside_project(project_root, args.baseline_results, kind="file")
    history_reports = [
        _inside_project(project_root, value, kind="file") for value in args.history_report
    ]
    prior_briefs = [
        _inside_project(project_root, value, kind="file") for value in args.prior_brief
    ]
    round_dir = _inside_project(project_root, args.round_dir, kind="output")
    round_id = args.round_id or round_dir.name

    if args.runner == "validate-only":
        if not round_dir.is_dir():
            raise FileNotFoundError(round_dir)
        manifest_path = round_dir / "round-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        candidates = _validate_outputs(
            project_root=project_root,
            round_dir=round_dir,
            incumbent=incumbent,
            candidate_count=args.candidate_count,
        )
        manifest["status"] = "candidates-ready"
        manifest["candidates"] = candidates
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(manifest_path, manifest)
        print(f"[skillboost] candidates ready: {manifest_path}")
        return 0

    if round_dir.exists():
        raise FileExistsError(f"round directory already exists: {round_dir}")

    (round_dir / "briefs").mkdir(parents=True)
    candidates_dir = round_dir / "candidates"
    candidates_dir.mkdir()
    for index in range(1, args.candidate_count + 1):
        shutil.copytree(incumbent, candidates_dir / f"candidate-{index}")

    context = round_dir / "attribution-context.md"
    _prepare_context(
        project_root=project_root,
        report=report,
        results=results,
        incumbent=incumbent,
        output=context,
        history_reports=history_reports,
        prior_briefs=prior_briefs,
    )
    prompt = _render_prompt(
        round_id=round_id,
        candidate_count=args.candidate_count,
        incumbent=_portable(incumbent, project_root),
        report=_portable(report, project_root),
        results=_portable(results, project_root),
        context=_portable(context, project_root),
        round_dir=_portable(round_dir, project_root),
    )
    prompt_path = round_dir / "evolution-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    manifest_path = round_dir / "round-manifest.json"
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "round_id": round_id,
        "status": "prepared",
        "incumbent": _portable(incumbent, project_root),
        "baseline_report": _portable(report, project_root),
        "baseline_results": _portable(results, project_root),
        "attribution_context": _portable(context, project_root),
        "evolution_prompt": _portable(prompt_path, project_root),
        "candidate_count": args.candidate_count,
        "runner": args.runner,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(manifest_path, manifest)

    if args.runner == "prepare-only":
        print(f"[skillboost] prepared evolution prompt: {prompt_path}")
        print("[skillboost] execute that prompt in Codex or Claude Code, then run --runner validate-only")
        return 0

    executable = shutil.which(args.claude_bin)
    if executable is None:
        manifest["status"] = "runner-unavailable"
        _write_json(manifest_path, manifest)
        print(f"Claude Code executable not found: {args.claude_bin}", file=sys.stderr)
        return 127
    command = [
        executable,
        "--print",
        "--bare",
        "--input-format",
        "text",
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--max-turns",
        str(args.max_turns),
        "--tools",
        "Read,Glob,Grep,Edit,Write",
    ]
    if args.model:
        command.extend(["--model", args.model])
    stream_path = round_dir / "evolution-model-stream.jsonl"
    stderr_path = round_dir / "evolution-model-stderr.log"
    final_result = ""
    with stream_path.open("w", encoding="utf-8") as stream, stderr_path.open(
        "w", encoding="utf-8"
    ) as errors:
        process = subprocess.Popen(
            command,
            cwd=project_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
            bufsize=1,
            env=os.environ.copy(),
        )
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(prompt)
        process.stdin.close()
        for line in process.stdout:
            stream.write(line)
            stream.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "result":
                final_result = str(event.get("result", ""))
        return_code = process.wait()
    (round_dir / "evolution-model-result.txt").write_text(final_result + "\n", encoding="utf-8")
    if return_code != 0:
        manifest["status"] = "runner-failed"
        manifest["runner_exit_code"] = return_code
        _write_json(manifest_path, manifest)
        return return_code

    try:
        candidates = _validate_outputs(
            project_root=project_root,
            round_dir=round_dir,
            incumbent=incumbent,
            candidate_count=args.candidate_count,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        manifest["status"] = "validation-failed"
        manifest["validation_error"] = str(error)
        _write_json(manifest_path, manifest)
        print(f"evolution output validation failed: {error}", file=sys.stderr)
        return 3
    manifest["status"] = "candidates-ready"
    manifest["candidates"] = candidates
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(manifest_path, manifest)
    print(f"[skillboost] candidates ready: {manifest_path}")
    print("[skillboost] next: evaluate and select them with skillboost-orchestrate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
