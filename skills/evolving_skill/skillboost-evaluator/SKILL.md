---
name: skillboost-evaluator
description: Normalize an agent-skill evaluation into auditable case records, aggregate metrics, slice metrics, and trace-integrity diagnostics. Use when evaluating a versioned task skill or preparing comparable evidence for a SkillBoost evolution round; do not use to diagnose or edit the skill.
---

# SkillBoost Evaluator

Produce trustworthy evidence for an evolution decision. Preserve raw trajectories and separate execution failure, parse failure, and task failure.

## Stage outputs

For one immutable run, preserve this generic artifact chain:

```text
<run-dir>/
├── traces/trace_<case-id>.json   one raw trajectory or explicit terminal artifact per completed case
└── evals/
    ├── results_<run>.jsonl       one normalized case record per dataset case
    └── report_<run>.json         aggregate metrics, case sets, slices, and run metadata
```

An interrupted run is still consumable: retain completed traces and represent every absent case as `missing` in the normalized outputs. Never overwrite an earlier run directory.

## Required inputs

- immutable skill identifier or checksum;
- dataset identifier, split, and case IDs;
- execution configuration, including model and decoding settings;
- one raw trace or explicit missing state per case;
- task-specific prediction parser and scoring rule.

If any of these are unavailable, record the omission. Do not infer missing predictions or silently drop cases.

## Procedure

1. Freeze the skill snapshot, dataset case IDs, evaluator/scorer revision, model settings, and execution configuration.
2. Execute every selected case and retain its raw trace under the run directory.
3. Normalize each case into one state: `correct`, `incorrect`, `unknown` (output cannot be scored), or `missing` (execution artifact absent).
4. Compute the primary metric only over its declared denominator. Report completion separately.
5. Compute predeclared slice metrics and resource use when available.
6. Emit an evaluation report conforming to `schemas/evaluation-report.schema.json`, including correct, incorrect, and undecided case IDs, and keep the case-level JSONL beside it.
7. Block downstream mutation when missing/unknown rates exceed the experiment's declared tolerance or when failures are primarily infrastructural.

For denominator rules, trace fields, leakage checks, and paired-comparison guidance, read [references/evaluation-protocol.md](references/evaluation-protocol.md).

When evaluating candidates for promotion, complete module 7 of each candidate's Repair Brief from measured artifacts, then write the human-readable verified decision with [references/acceptance-record-template.md](references/acceptance-record-template.md). Its machine-readable companion is the Evolution Record defined by `schemas/evolution-record.schema.json`.

## Invariants

- Raw traces are the evidence source; aggregate reports never replace them.
- Repeated runs never overwrite earlier artifacts.
- Percentages are normalized to `[0, 1]` in the public report contract.
- `incorrect_cases` and `undecided_cases` contain stable IDs, not display text.
- Dataset-specific adapters may add metrics but may not reinterpret common fields.
- A directed failed-case run is a screening measurement, not promotion evidence.
- Acceptance thresholds are frozen before candidate results are observed.

## Deterministic helper

For exact-match JSONL tasks, `scripts/normalize_run.py` normalizes a directory of traces:

```bash
python3 scripts/normalize_run.py \
  --run-dir runs/example \
  --data data/dev.jsonl \
  --skill-version v0 \
  --dataset-id example/dev \
  --label-field answer \
  --prediction-field answer
```

Use a benchmark adapter when scoring requires execution, structured equivalence, environment success, or an external judge.

## Handoff

For a baseline run, return paths to `traces/`, the case-level results, and the report; state the missing and unknown rates; and identify whether the run is admissible for attribution. For candidate selection, additionally return one directed-screen report per candidate, one full-set report per finalist, the completed Repair Brief back-testing fields, and the Verified Acceptance Record. Do not propose repairs—that belongs to the Analyzer and Mutator stages.
