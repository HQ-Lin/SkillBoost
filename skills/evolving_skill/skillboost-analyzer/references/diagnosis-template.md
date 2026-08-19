# Shared Diagnosis template

Use this template for the evidence-grounded diagnosis \(g_t\) produced once per evolution round. It is shared unchanged by every candidate Repair Brief in that round. The machine-readable companion must conform to `schemas/diagnosis.schema.json`.

Do not propose candidate-specific edits here. Diagnosis records what failed, why it failed, where the causal defect is located, and which evidence would falsify that attribution.

```markdown
---
artifact: skillboost-shared-diagnosis
schema_version: "1.0"
diagnosis_id: diagnosis-<round-id>
round_id: <round-id>
source_run: <evaluation-run-id>
parent_skill: <name>@<version>
parent_sha256: <64 lowercase hex characters>
status: complete
---

# Shared Diagnosis: <parent version> → <round id>

## 1. Metadata Header

| Field | Value |
|---|---|
| Model and decoding configuration | <immutable run configuration or config reference> |
| Dataset and split | <dataset>/<split> |
| Primary metric and direction | <metric>, <maximize/minimize> |
| Trace coverage | <available>/<expected> (<rate>) |
| Fixed screening set | <failed and undecided case-set artifact> |

## 2. Baseline Performance Summary

| Slice | Correct/decided | Primary metric | Completion | Notes |
|---|---:|---:|---:|---|
| Overall | <n>/<n> | <value> | <value> | <observation> |
| <predeclared slice> | <n>/<n> | <value> | <value> | <observation> |

State the empirical observation without proposing a repair. Distinguish task failure from missing traces, parse failures, label issues, and infrastructure faults.

## 3. Failure Mode Cluster Analysis

### Cluster <C-001>: <causal mechanism>

- Case IDs: `<stable-id>`, `<stable-id>`
- Defect class: `<missing_strategy | ambiguous_strategy | overbroad_strategy | broken_control_flow | knowledge_gap | output_contract | capability_gap>`
- Earliest causal error: <first decision that diverges from the desired process>
- Incumbent skill location: `<file > section or line-stable anchor>`
- Trace evidence: <independently locatable excerpts or trace-step references>
- Root cause: <why the incumbent instruction caused or allowed the error>
- Counterfactual: <instruction-level condition that would likely have prevented the failure>
- Competing hypothesis: <alternative explanation, or `none supported`>
- Confidence: <0–1>
- Disposition: `<repair | decompose | rerun | adjudicate>`

Repeat for each causal cluster. Do not cluster by topic alone.

## Quarantined Cases

| Case ID | Reason | Evidence | Required next action |
|---|---|---|---|
| <id> | <engineering_anomaly/label_issue> | <trace or record reference> | <rerun/adjudicate> |

Use `None` when no cases are quarantined.

## Unresolved Hypotheses

| Hypothesis | Missing evidence | Resolution test |
|---|---|---|
| <alternative cause> | <what is not known> | <measurement or replay needed> |

Use `None` when the evidence discriminates all retained causal hypotheses.

## Diagnosis Invariants

- Fixed failed/undecided screening case IDs: `<artifact or explicit stable IDs>`
- Must-maintain correct-case slices: `<slice names or artifact>`
- Trace-integrity threshold: `<declared threshold>`
- Candidate-independent constraints: <constraints every strategy must preserve>
```

The evidence chain for every repairable cluster must be complete:

```text
case IDs → trace evidence → earliest causal error → incumbent location
         → counterfactual condition → observable resolution test
```
