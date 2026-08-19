# Evaluation protocol

## Case record

Each JSONL case record should include:

| Field | Meaning |
|---|---|
| `task_id` | Stable dataset identifier |
| `ground_truth` | Raw scoring target or target reference |
| `prediction` | Parsed agent prediction, if available |
| `status` | `correct`, `incorrect`, `unknown`, or `missing` |
| `trace_file` | Path or content identifier for the raw trajectory |
| `parser_revision` | Version of the prediction/scoring adapter |
| `group` | Optional predeclared slice identifier |
| `cost` | Optional tokens, tool calls, and wall time |

## Denominators

- `completion_rate = decided / total`, where decided means a scoreable prediction exists.
- For exact-match tasks, `accuracy = correct / total` is preferred for promotion because it penalizes non-completion. If a benchmark convention uses `correct / decided`, report both and declare which is primary.
- Never exclude parser failures after observing their answers.

## Trace integrity

Check that every selected case has exactly one terminal state, traces refer to the frozen skill version, and case IDs are unique. Report missing and malformed artifacts independently. Repair provider, timeout, truncation, or parser failures before causal attribution when they dominate the error set.

## Leakage controls

Keep development failures separate from held-out reporting. A repair may use development trajectories but must not include case-specific answers, hidden labels, or identifiers. Freeze the held-out evaluator before evolution begins.

## Comparisons

Compare incumbent and candidate on identical cases and configurations. For binary outcomes, retain the paired 2x2 table required by McNemar's test. For arbitrary metrics, retain per-case values for paired bootstrap confidence intervals. Report all attempted candidates and rounds to make repeated selection visible.

