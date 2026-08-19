from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from skillboost.orchestrate import write_promotion_artifacts


ROOT = Path(__file__).resolve().parents[1]


class HelperScriptTests(unittest.TestCase):
    def test_evolution_runner_prepares_agent_round_without_calling_evaluator(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_value:
            tmp = Path(tmp_value)
            incumbent = tmp / "incumbent"
            incumbent.mkdir()
            (incumbent / "SKILL.md").write_text(
                "---\nname: generic-task\ndescription: Solve a generic task.\n---\n\n# Workflow\n",
                encoding="utf-8",
            )
            run_dir = tmp / "baseline-run"
            evals = run_dir / "evals"
            traces = run_dir / "traces"
            evals.mkdir(parents=True)
            traces.mkdir()
            report = evals / "report.json"
            report.write_text(
                json.dumps(
                    {
                        "run_id": "baseline",
                        "skill_version": "v0",
                        "metrics": {"accuracy": 0.0, "completion_rate": 1.0},
                        "incorrect_cases": ["case-a"],
                    }
                ),
                encoding="utf-8",
            )
            results = evals / "results.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "case-a",
                        "status": "incorrect",
                        "ground_truth": "target",
                        "prediction": "other",
                        "trace_file": "traces/trace_case-a.json",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (traces / "trace_case-a.json").write_text(
                json.dumps({"result_text": "candidate output"}), encoding="utf-8"
            )
            round_dir = tmp / "round-1"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "skillboost.evolve",
                    "--incumbent",
                    str(incumbent.relative_to(ROOT)),
                    "--baseline-report",
                    str(report.relative_to(ROOT)),
                    "--baseline-results",
                    str(results.relative_to(ROOT)),
                    "--round-dir",
                    str(round_dir.relative_to(ROOT)),
                    "--round-id",
                    "round-1",
                    "--candidate-count",
                    "2",
                    "--runner",
                    "prepare-only",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            prompt = (round_dir / "evolution-prompt.md").read_text(encoding="utf-8")
            manifest = json.loads((round_dir / "round-manifest.json").read_text(encoding="utf-8"))
            self.assertIn("You are the evolution model, not the benchmark task model", prompt)
            self.assertIn("skillboost-analyzer/SKILL.md", prompt)
            self.assertIn("skillboost-mutator/SKILL.md", prompt)
            self.assertNotIn("DashScope", prompt)
            self.assertEqual(manifest["status"], "prepared")
            self.assertNotIn(str(ROOT), json.dumps(manifest))
            for index in (1, 2):
                self.assertTrue((round_dir / f"candidates/candidate-{index}/SKILL.md").is_file())

    def test_normalize_run_preserves_missing_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_value:
            tmp = Path(tmp_value)
            data = tmp / "data.jsonl"
            data.write_text(
                json.dumps({"task_id": "a", "answer": "42"})
                + "\n"
                + json.dumps({"task_id": "b", "answer": "7"})
                + "\n",
                encoding="utf-8",
            )
            run_dir = tmp / "run"
            traces = run_dir / "traces"
            traces.mkdir(parents=True)
            (traces / "trace_a.json").write_text(
                json.dumps({"result_text": '{"answer": "42"}'}), encoding="utf-8"
            )
            script = (
                ROOT
                / "skills/evolving_skill/skillboost-evaluator/scripts/normalize_run.py"
            )
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--run-dir",
                    str(run_dir),
                    "--data",
                    str(data),
                    "--skill-version",
                    "v0",
                    "--dataset-id",
                    "synthetic/dev",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report_path = next((run_dir / "evals").glob("report_*.json"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["metrics"]["accuracy"], 0.5)
            self.assertEqual(report["metrics"]["completion_rate"], 0.5)
            self.assertEqual(report["undecided_cases"], ["b"])

    def test_candidate_validator_accepts_bounded_mounted_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_value:
            tmp = Path(tmp_value)
            incumbent = tmp / "v0"
            candidate = tmp / "candidate"
            for root, body in (
                (incumbent, "# Example\n\nRead [rules](references/rules.md).\n"),
                (candidate, "# Example\n\nAlways read [rules](references/rules.md).\n"),
            ):
                (root / "references").mkdir(parents=True)
                (root / "SKILL.md").write_text(
                    "---\nname: example\ndescription: Solve the example task.\n---\n\n" + body,
                    encoding="utf-8",
                )
                (root / "references/rules.md").write_text("# Rules\n", encoding="utf-8")
            script = (
                ROOT
                / "skills/evolving_skill/skillboost-mutator/scripts/validate_candidate.py"
            )
            completed = subprocess.run(
                [sys.executable, str(script), str(incumbent), str(candidate)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(
                (candidate / "candidate-validation.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["valid"])
            self.assertEqual(report["changed_files"][0]["path"], "SKILL.md")

    def test_repair_brief_validator_enforces_lifecycle_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_value:
            tmp = Path(tmp_value)
            brief = tmp / "repair-brief.md"
            headings = [
                "## 1. Metadata Header",
                "## 2. Baseline Performance Summary",
                "## 3. Failure Mode Cluster Analysis",
                "## 4. Repair Strategy (Repair Actions)",
                "## 5. Repair Action Mapping Table",
                "## 6. Anti-Regression Guardrails",
                "## 7. Back-Testing Results (Post-evolution)",
                "## 8. Execution Plan",
            ]
            brief.write_text(
                "---\n"
                "artifact: skillboost-repair-brief\n"
                'schema_version: "1.0"\n'
                "brief_id: brief-r1-1\n"
                "diagnosis_id: diagnosis-r1\n"
                "strategy_id: strategy-r1-1\n"
                "candidate_id: candidate-1\n"
                "status: draft\n"
                "---\n\n# Repair Brief\n\n"
                + "\n\ncontent\n\n".join(headings)
                + "\n",
                encoding="utf-8",
            )
            script = (
                ROOT
                / "skills/evolving_skill/skillboost-mutator/scripts/validate_repair_brief.py"
            )
            draft = subprocess.run(
                [sys.executable, str(script), str(brief), "--stage", "draft"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(draft.returncode, 0, draft.stdout)

            evaluated = subprocess.run(
                [sys.executable, str(script), str(brief), "--stage", "evaluated"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(evaluated.returncode, 0)
            self.assertIn("evaluated validation requires", evaluated.stdout)

    def test_attribution_context_tracks_history_and_regressions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_value:
            tmp = Path(tmp_value)
            run_dir = tmp / "run"
            evals = run_dir / "evals"
            traces = run_dir / "traces"
            evals.mkdir(parents=True)
            traces.mkdir()
            current = evals / "report_current.json"
            current.write_text(
                json.dumps(
                    {
                        "run_id": "current",
                        "skill_version": "v1",
                        "metrics": {"accuracy": 0.5},
                        "incorrect_cases": ["case-a"],
                    }
                ),
                encoding="utf-8",
            )
            history = tmp / "report_previous.json"
            history.write_text(
                json.dumps(
                    {
                        "run_id": "previous",
                        "skill_version": "v0",
                        "metrics": {"accuracy": 1.0},
                        "correct_cases": ["case-a"],
                    }
                ),
                encoding="utf-8",
            )
            results = evals / "results_current.jsonl"
            results.write_text(
                json.dumps(
                    {
                        "task_id": "case-a",
                        "status": "incorrect",
                        "ground_truth": "target",
                        "prediction": "other",
                        "trace_file": "traces/trace_case-a.json",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (traces / "trace_case-a.json").write_text(
                json.dumps({"result_text": "terminal output"}), encoding="utf-8"
            )
            skill = tmp / "SKILL.md"
            skill.write_text("# Generic skill\n\n## Workflow\n", encoding="utf-8")
            brief = tmp / "brief_previous.md"
            brief.write_text(
                "---\nstatus: rejected\n---\n\n# Repair Brief: previous\n",
                encoding="utf-8",
            )
            output = tmp / "attribution-context.md"
            script = (
                ROOT
                / "skills/evolving_skill/skillboost-analyzer/scripts/prepare_context.py"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(current),
                    str(results),
                    str(skill),
                    "--history-report",
                    str(history),
                    "--prior-brief",
                    str(brief),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            context = output.read_text(encoding="utf-8")
            self.assertIn("Case `case-a` was correct in earlier version(s): `v0`", context)
            self.assertIn("brief_previous.md", context)
            self.assertNotIn(str(tmp), context)

    def test_promotion_artifacts_create_manifest_and_external_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_value:
            tmp = Path(tmp_value)
            destination = tmp / "versions" / "v1"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text(
                "---\nname: generic-skill\ndescription: Perform a generic task.\n---\n",
                encoding="utf-8",
            )
            winner = {"candidate": "candidate-1"}
            record = {
                "schema_version": "1.0",
                "round_id": "round-1",
                "incumbent": "runs/baseline/report.json",
                "brief_id": "brief-default",
                "candidates": [
                    {
                        "candidate": "candidate-1",
                        "brief_id": "brief-1",
                        "report_path": "runs/candidate-1/report.json",
                        "assessment": {
                            "improvement": 0.1,
                            "completion_rate": 1.0,
                            "case_regression_rate": 0.0,
                            "fix_rate": 0.1,
                            "slice_regressions": {},
                        },
                    }
                ],
                "created_at": "2026-08-19T00:00:00+00:00",
            }
            manifest_path, changelog_path = write_promotion_artifacts(destination, winner, record)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["brief_id"], "brief-1")
            self.assertEqual(manifest["decision"], "promoted")
            self.assertTrue(changelog_path.is_file())
            self.assertNotIn("## Changelog", (destination / "SKILL.md").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
