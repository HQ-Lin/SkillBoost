# Repair Brief template

A Repair Brief is the paper-aligned intermediate artifact

\[
b_t^{(n)} = (g_t,\,\pi^{(n)}), \qquad n=1,\ldots,N.
\]

Create one brief per candidate. Modules 1–3 must reproduce or reference the same immutable Shared Diagnosis \(g_t\); modules 4–5 contain the candidate-specific strategy \(\pi^{(n)}\); module 6 declares gates before evaluation; modules 7–8 are completed as the candidate is tested and decided. The machine-readable companion must conform to `schemas/repair-brief.schema.json`.

```markdown
---
artifact: skillboost-repair-brief
schema_version: "1.0"
brief_id: brief-<round-id>-<n>
diagnosis_id: diagnosis-<round-id>
strategy_id: strategy-<round-id>-<n>
candidate_id: candidate-<n>
status: draft
---

# Repair Brief: <source version> → <candidate id>

## 1. Metadata Header

| Field | Value |
|---|---|
| Source skill | <name>@<version> |
| Target candidate | <candidate id / proposed version> |
| Parent SHA-256 | <64 lowercase hex characters> |
| Model configuration | <immutable config or reference> |
| Dataset and split | <dataset>/<split> |
| Source run | <evaluation run ID> |
| Shared diagnosis | <diagnosis ID and artifact path> |

## 2. Baseline Performance Summary

| Slice | Correct/decided | Primary metric | Completion | Notes |
|---|---:|---:|---:|---|
| Overall | <n>/<n> | <value> | <value> | <observation> |
| <predeclared slice> | <n>/<n> | <value> | <value> | <observation> |

This module is inherited from the Shared Diagnosis and must be identical across candidates.

## 3. Failure Mode Cluster Analysis

### Cluster <C-001>: <causal mechanism>

- Case IDs: `<stable IDs>`
- Earliest causal error: <decision-level error>
- Root cause: <instruction-level cause>
- Incumbent skill location: `<file > section>`
- Representative trace evidence: <locatable evidence>
- Confidence and disposition: <value>, <repair/decompose/...>

Include every cluster from the Shared Diagnosis, even when this candidate deliberately does not address it.

## 4. Repair Strategy (Repair Actions)

### Strategy π(<n>): <short thesis>

- Priority: <selected cluster ordering>
- Edit scope: `<narrow | wider | decomposition>`
- Causal hypothesis tested: <falsifiable statement>
- Difference from other candidates: <material difference>

#### Action <A-001>: <action title>

- Addresses: `<C-001>`
- Operator: `<ADD | REFINE | REORDER | PRUNE | DECOMPOSE>`
- Target: `<file > section>`
- Current behavior or text: <concise description>
- Proposed behavior or text: <bounded edit specification>
- Applicability: <positive conditions>
- Non-applicability: <exclusions>
- Expected effect: <observable behavior>
- Falsification check: <result that would reject the hypothesis>

## 5. Repair Action Mapping Table

| Failure cluster | Root cause | Action ID | Repair operator | SKILL.md location | Expected effect |
|---|---|---|---|---|---|
| C-001 | <cause> | A-001 | REFINE | <section> | <effect> |

Every action maps to at least one diagnosed cluster; every selected cluster maps to at least one action.

## 6. Anti-Regression Guardrails

### Must-maintain strengths

| Protected behavior or slice | Baseline | Minimum acceptable value | Measurement |
|---|---:|---:|---|
| <behavior/slice> | <value> | <threshold> | <metric or invariant> |

### Predeclared rejection criteria

| Gate | Threshold | Direction | Evidence source |
|---|---:|---|---|
| Primary improvement | <min improvement> | maximize gain | full evaluation report |
| Completion | <minimum> | at least | full evaluation report |
| Case-level regression | <maximum> | at most | paired case comparison |
| Worst protected-slice regression | <maximum> | at most | slice metrics |
| Changed lines | <maximum> | at most | candidate validation |
| Skill growth | <maximum> | at most | candidate validation |

The targeted screen ranks candidates but cannot authorize promotion.

## 7. Back-Testing Results (Post-evolution)

Set the brief status to `evaluated` only after this module is complete.

### Targeted screen

| Case set | Baseline | Candidate | Fixes | Regressions | Result |
|---|---:|---:|---:|---:|---|
| Fixed failed/undecided set | <value> | <value> | <n> | <n> | <advance/reject> |

### Full-set evaluation

| Metric or slice | Baseline | Candidate | Change | Gate result |
|---|---:|---:|---:|---|
| Primary metric | <value> | <value> | <signed change> | pass/fail |
| Completion | <value> | <value> | <signed change> | pass/fail |
| <protected slice> | <value> | <value> | <signed change> | pass/fail |

- Structural validation: <pass/fail and artifact>
- Cost and complexity: <comparison>
- Repaired case IDs: <stable IDs or artifact>
- Regressed case IDs: <stable IDs or artifact>
- Report paths: <portable artifact paths>

## 8. Execution Plan

| Step | Owner | Status | Evidence artifact |
|---|---|---|---|
| Freeze diagnosis and candidate strategy | Analyzer/Mutator | complete | <path> |
| Copy incumbent and apply bounded edit | Mutator | <pending/complete/failed> | <candidate path/diff> |
| Validate structure, provenance, and budget | Mutator | <pending/complete/failed> | <validation report> |
| Run fixed-set targeted screen | Evaluator | <pending/complete/failed> | <report> |
| Run Top-K full evaluation | Evaluator | <pending/complete/failed> | <report> |
| Apply all acceptance gates | Orchestrator | <pending/complete/failed> | <acceptance record> |
| Promote candidate or retain incumbent | Orchestrator | <pending/accepted/rejected> | <evolution record> |

### Final decision

- Decision: `<pending | accepted | rejected>`
- Reason: <gate-based explanation>
- Resulting state: <promoted version or retained incumbent>
```

Do not fill post-evolution results with predictions. Preserve the draft and append measured results so the predeclared strategy and gates remain auditable.
