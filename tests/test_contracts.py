from __future__ import annotations

import unittest

from skillboost.contracts import (
    SelectionPolicy,
    candidate_assessment,
    extract_failure_ids,
    metric_value,
)


class ContractTests(unittest.TestCase):
    def test_extract_failure_ids_supports_public_and_legacy_shapes(self) -> None:
        report = {
            "incorrect_cases": ["a", {"task_id": "b"}],
            "fp_cases": [{"task_id": "b"}, {"task_id": "c"}],
            "missing_task_ids": [4],
        }
        self.assertEqual(extract_failure_ids(report), ["a", "b", "c", "4"])

    def test_metric_value_normalizes_legacy_percentages(self) -> None:
        self.assertEqual(metric_value({"accuracy": 75}, "accuracy"), 0.75)
        self.assertEqual(metric_value({"metrics": {"accuracy": 0.75}}, "accuracy"), 0.75)

    def test_candidate_passes_direction_aware_gates(self) -> None:
        baseline = {
            "metrics": {"accuracy": 0.70, "completion_rate": 0.99},
            "slice_metrics": {"easy": {"accuracy": 0.80}, "hard": {"accuracy": 0.60}},
        }
        candidate = {
            "metrics": {"accuracy": 0.74, "completion_rate": 0.98},
            "slice_metrics": {"easy": {"accuracy": 0.79}, "hard": {"accuracy": 0.69}},
        }
        policy = SelectionPolicy(
            min_improvement=0.03,
            max_slice_regression=0.02,
            min_completion=0.95,
        )
        assessment = candidate_assessment(baseline, candidate, policy)
        self.assertTrue(assessment["eligible"])
        self.assertAlmostEqual(assessment["improvement"], 0.04)

    def test_candidate_fails_slice_gate_despite_global_gain(self) -> None:
        baseline = {"accuracy": 0.70, "per_group": {"a": 0.80, "b": 0.60}, "pass_rate": 1.0}
        candidate = {"accuracy": 0.75, "per_group": {"a": 0.70, "b": 0.80}, "pass_rate": 1.0}
        assessment = candidate_assessment(
            baseline,
            candidate,
            SelectionPolicy(max_slice_regression=0.05),
        )
        self.assertFalse(assessment["eligible"])
        self.assertAlmostEqual(assessment["slice_regressions"]["a"], 0.10)

    def test_minimized_metric_uses_reversed_direction(self) -> None:
        assessment = candidate_assessment(
            {"metrics": {"error_rate": 0.20, "completion_rate": 1.0}},
            {"metrics": {"error_rate": 0.15, "completion_rate": 1.0}},
            SelectionPolicy(
                metric_key="error_rate",
                metric_direction="minimize",
                min_improvement=0.04,
            ),
        )
        self.assertTrue(assessment["eligible"])
        self.assertAlmostEqual(assessment["improvement"], 0.05)

    def test_missing_protected_slice_fails_gate(self) -> None:
        assessment = candidate_assessment(
            {
                "metrics": {"accuracy": 0.5, "completion_rate": 1.0},
                "slice_metrics": {"protected": {"accuracy": 0.5}},
            },
            {"metrics": {"accuracy": 0.6, "completion_rate": 1.0}},
            SelectionPolicy(),
        )
        self.assertFalse(assessment["eligible"])
        self.assertIn("missing protected slice", assessment["reasons"][0])

    def test_verified_acceptance_counts_case_regressions(self) -> None:
        baseline = {
            "total": 4,
            "metrics": {"accuracy": 0.5, "completion_rate": 1.0},
            "correct_cases": ["a", "b"],
            "incorrect_cases": ["c", "d"],
        }
        candidate = {
            "total": 4,
            "metrics": {"accuracy": 0.75, "completion_rate": 1.0},
            "correct_cases": ["a", "c", "d"],
            "incorrect_cases": ["b"],
        }
        assessment = candidate_assessment(
            baseline,
            candidate,
            SelectionPolicy(max_case_regression=0.30),
        )
        self.assertTrue(assessment["eligible"])
        self.assertEqual(assessment["fix_rate"], 0.5)
        self.assertEqual(assessment["case_regression_rate"], 0.25)


if __name__ == "__main__":
    unittest.main()
