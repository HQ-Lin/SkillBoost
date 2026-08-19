"""Compatibility helpers and promotion invariants for SkillBoost artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


def _case_id(value: Any) -> str | None:
    if isinstance(value, (str, int)):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("task_id", "case_id", "id"):
            if value.get(key) is not None:
                return str(value[key])
    return None


def unique_case_ids(values: Iterable[Any]) -> list[str]:
    """Return stable, order-preserving identifiers from legacy or v1 records."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        identifier = _case_id(value)
        if identifier and identifier not in seen:
            seen.add(identifier)
            result.append(identifier)
    return result


def extract_failure_ids(report: Mapping[str, Any], fail_ids_key: str | None = None) -> list[str]:
    """Extract the fixed directed set from a normalized or legacy report."""
    if fail_ids_key:
        return unique_case_ids(report.get(fail_ids_key, []) or [])

    values: list[Any] = []
    for key in (
        "incorrect_cases",
        "undecided_cases",
        "fp_cases",
        "fn_cases",
        "fail_ids",
        "missing_task_ids",
    ):
        values.extend(report.get(key, []) or [])
    return unique_case_ids(values)


def metric_value(report: Mapping[str, Any], key: str) -> float | None:
    """Read a v1 or legacy metric and normalize percentages to fractions."""
    metrics = report.get("metrics", {})
    value = metrics.get(key) if isinstance(metrics, Mapping) else None
    if value is None:
        value = report.get(key)
    if not isinstance(value, (int, float)):
        return None
    result = float(value)
    if 1.0 < result <= 100.0:
        result /= 100.0
    return result


def completion_rate(report: Mapping[str, Any]) -> float:
    explicit = metric_value(report, "completion_rate")
    if explicit is None:
        explicit = metric_value(report, "pass_rate")
    if explicit is not None:
        return explicit
    total = report.get("total", 0)
    decided = report.get("decided", report.get("completed", 0))
    if isinstance(total, (int, float)) and total > 0 and isinstance(decided, (int, float)):
        return float(decided) / float(total)
    return 0.0


def slice_values(report: Mapping[str, Any], metric_key: str, group_key: str) -> dict[str, float]:
    """Normalize v1 slice metrics and common legacy per-group layouts."""
    groups = report.get("slice_metrics")
    if not isinstance(groups, Mapping):
        groups = report.get(group_key, {})
    if not isinstance(groups, Mapping):
        return {}

    normalized: dict[str, float] = {}
    for name, entry in groups.items():
        value: Any = entry
        if isinstance(entry, Mapping):
            value = entry.get(metric_key, entry.get("accuracy", entry.get("value")))
        if isinstance(value, (int, float)):
            number = float(value)
            if 1.0 < number <= 100.0:
                number /= 100.0
            normalized[str(name)] = number
    return normalized


@dataclass(frozen=True)
class SelectionPolicy:
    metric_key: str = "accuracy"
    metric_direction: str = "maximize"
    min_improvement: float = 0.0
    max_case_regression: float | None = None
    max_slice_regression: float = 0.0
    min_completion: float = 0.0
    group_key: str = "per_group"

    def __post_init__(self) -> None:
        if self.metric_direction not in {"maximize", "minimize"}:
            raise ValueError("metric_direction must be 'maximize' or 'minimize'")
        if self.max_slice_regression < 0:
            raise ValueError("max_slice_regression must be non-negative")
        if self.max_case_regression is not None and self.max_case_regression < 0:
            raise ValueError("max_case_regression must be non-negative")
        if not 0 <= self.min_completion <= 1:
            raise ValueError("min_completion must be in [0, 1]")


def directed_delta(baseline: float, candidate: float, direction: str) -> float:
    """Return positive values for improvements, independent of metric direction."""
    return candidate - baseline if direction == "maximize" else baseline - candidate


def candidate_assessment(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    policy: SelectionPolicy,
) -> dict[str, Any]:
    """Apply full-set promotion gates to one candidate report."""
    baseline_value = metric_value(baseline, policy.metric_key)
    candidate_value = metric_value(candidate, policy.metric_key)
    reasons: list[str] = []

    if baseline_value is None or candidate_value is None:
        improvement = None
        reasons.append(f"missing primary metric: {policy.metric_key}")
    else:
        improvement = directed_delta(baseline_value, candidate_value, policy.metric_direction)
        if improvement < policy.min_improvement:
            reasons.append(
                f"improvement {improvement:.6f} is below required {policy.min_improvement:.6f}"
            )

    completion = completion_rate(candidate)
    if completion < policy.min_completion:
        reasons.append(
            f"completion {completion:.6f} is below required {policy.min_completion:.6f}"
        )

    baseline_total = baseline.get("total")
    candidate_total = candidate.get("total")
    if (
        isinstance(baseline_total, int)
        and isinstance(candidate_total, int)
        and baseline_total != candidate_total
    ):
        reasons.append(
            f"full-set size changed from {baseline_total} to {candidate_total}"
        )

    total = baseline_total if isinstance(baseline_total, int) and baseline_total > 0 else None
    baseline_correct = set(unique_case_ids(baseline.get("correct_cases", []) or []))
    candidate_correct = set(unique_case_ids(candidate.get("correct_cases", []) or []))
    candidate_failed = set(extract_failure_ids(candidate))
    baseline_failed = set(extract_failure_ids(baseline))
    fix_rate = len(baseline_failed & candidate_correct) / total if total else None
    case_regression_rate = len(baseline_correct & candidate_failed) / total if total else None
    if policy.max_case_regression is not None:
        if not baseline_correct or total is None:
            reasons.append("case-level regression gate requires total and correct_cases")
        elif case_regression_rate is not None and case_regression_rate >= policy.max_case_regression:
            reasons.append(
                f"case regression {case_regression_rate:.6f} is not below "
                f"required {policy.max_case_regression:.6f}"
            )

    baseline_slices = slice_values(baseline, policy.metric_key, policy.group_key)
    candidate_slices = slice_values(candidate, policy.metric_key, policy.group_key)
    regressions: dict[str, float] = {}
    for name in sorted(set(baseline_slices) - set(candidate_slices)):
        reasons.append(f"candidate report is missing protected slice {name!r}")
    for name in sorted(set(baseline_slices) & set(candidate_slices)):
        improvement_on_slice = directed_delta(
            baseline_slices[name], candidate_slices[name], policy.metric_direction
        )
        if improvement_on_slice < 0:
            regression = -improvement_on_slice
            regressions[name] = regression
            if regression > policy.max_slice_regression:
                reasons.append(
                    f"slice {name!r} regressed by {regression:.6f}; "
                    f"limit is {policy.max_slice_regression:.6f}"
                )

    return {
        "eligible": not reasons,
        "baseline_metric": baseline_value,
        "candidate_metric": candidate_value,
        "improvement": improvement,
        "completion_rate": completion,
        "fix_rate": fix_rate,
        "case_regression_rate": case_regression_rate,
        "slice_regressions": regressions,
        "reasons": reasons,
        "policy": asdict(policy),
    }
