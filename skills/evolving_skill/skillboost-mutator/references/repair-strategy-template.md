# Repair Strategy template

Use this compact worksheet to diversify candidate-specific strategies \(\pi^{(n)}\) before editing any skill. Every strategy in a Best-of-\(N\) population must share the same diagnosis and differ in a scientifically meaningful priority, edit scope, or causal hypothesis.

```markdown
---
artifact: skillboost-repair-strategy
schema_version: "1.0"
strategy_id: strategy-<round-id>-<n>
diagnosis_id: diagnosis-<round-id>
candidate_id: candidate-<n>
---

# Repair Strategy π(<n>)

## Strategy Thesis

- Selected failure clusters: `<C-...>`
- Priority rule: <why these clusters are addressed first>
- Edit scope: `<narrow | wider | decomposition>`
- Causal hypothesis tested: <falsifiable hypothesis>
- Distinguishing feature: <how this differs materially from the other candidates>

## Planned Actions

| Action ID | Cluster | Operator | Target location | Intended edit | Expected behavioral effect |
|---|---|---|---|---|---|
| A-001 | C-001 | ADD/REFINE/REORDER/PRUNE/DECOMPOSE | <file > section> | <bounded edit> | <observable effect> |

## Interference Analysis

- Overlapping incumbent rules: <locations or `none`>
- Applicability boundary: <where the new rule applies>
- Non-applicability boundary: <where it must not apply>
- Priority relative to existing rules: <explicit precedence>
- Primary regression risk: <how a previously correct behavior could break>

## Falsification and Budget

- Targeted success criterion: <case/slice-level observable check>
- Full-set acceptance dependency: <required promotion gates>
- Maximum changed lines: <integer>
- Maximum skill growth ratio: <number>
- Stop condition: <condition under which this strategy is rejected or decomposed>
```

Do not create variants that only paraphrase the same planned edits.
