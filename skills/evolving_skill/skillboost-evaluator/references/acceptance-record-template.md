# Verified Acceptance Record template

Use this template after candidate back-testing to make the acceptance decision auditable. It is a human-readable view of the corresponding `schemas/evolution-record.schema.json` record; numerical claims must be copied from immutable evaluation and validation artifacts.

```markdown
---
artifact: skillboost-acceptance-record
schema_version: "1.0"
round_id: <round-id>
brief_id: <winning-or-best-tested-brief-id>
status: decided
---

# Verified Acceptance Record: <round id>

## Frozen Inputs

| Input | Artifact |
|---|---|
| Incumbent | <portable path and checksum> |
| Shared diagnosis | <diagnosis ID/path> |
| Candidate Repair Briefs | <brief IDs/paths> |
| Baseline report | <portable path> |
| Selection policy | <predeclared policy/path> |

## Phase A: Directed Screening

| Rank | Candidate | Strategy | Fixed-set score | Screen report | Advanced |
|---:|---|---|---:|---|---|
| 1 | <candidate> | <strategy ID> | <value> | <path> | yes/no |

State the fixed failed/undecided case set and deterministic guard sample. Screening results are ranking evidence only.

## Phase B: Full-Set Gate Matrix

| Candidate | Primary gain | Completion | Case regression | Worst slice regression | Structure/budget | Eligible |
|---|---:|---:|---:|---:|---|---|
| <candidate> | <value> | <value> | <value> | <value> | pass/fail | yes/no |

## Paired Outcome Accounting

| Candidate | Repaired cases | Regressed cases | Unchanged correct | Unchanged failed |
|---|---:|---:|---:|---:|
| <candidate> | <n> | <n> | <n> | <n> |

- Repaired case IDs: <artifact or stable IDs>
- Regressed case IDs: <artifact or stable IDs>
- Missing/unknown differences: <comparison>

## Decision

- Status: `<promoted | rejected>`
- Winner: <candidate ID or `none`>
- Gate-based reasons: <complete pass/failure rationale>
- Tie-breaker, if used: <predeclared rule and values>
- Resulting state: <new version or retained incumbent>

## Provenance

- Candidate checksum(s): <IDs and hashes>
- Evaluation configuration: <immutable configuration reference>
- Evaluation report(s): <portable paths>
- Candidate validation report(s): <portable paths>
- Evolution record: <portable JSON path>
- Decision timestamp: <UTC ISO 8601>
```

Never promote from the directed screen alone. If no candidate passes every full-set gate, record rejection and retain the incumbent.
