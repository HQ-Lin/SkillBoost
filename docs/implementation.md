# Implementation map

The repository separates agent-mediated reasoning from deterministic selection.

| Paper component | Implementation |
|---|---|
| Forward rollout | `benchmarks/evaluators/` for task execution, trajectory capture, and scoring |
| Structured exploitation | `skills/evolving_skill/skillboost-analyzer/` |
| Shared diagnosis \(g_t\) | `skillboost-analyzer/references/diagnosis-template.md` and `schemas/diagnosis.schema.json` |
| Candidate Repair Brief \(b_t^{(n)}\) | `skillboost-mutator/references/repair-brief-template.md` and `schemas/repair-brief.schema.json` |
| Prior-guided exploration | `skills/evolving_skill/skillboost-mutator/` |
| Evolution-model execution | `src/skillboost/evolve.py` for Claude Code or prepared interactive execution |
| Candidate validation | `skillboost-mutator/scripts/validate_candidate.py` |
| Verified acceptance | `skills/evolving_skill/skillboost-evaluator/` and `src/skillboost/orchestrate.py` |
| Versioned seed states | `examples/seed-skills/` |
| Ablations and analysis | `experiments/` and `analysis/` |

## Evolution artifacts

```text
skill s_t
  └── rollout traces
       └── evaluation report
            └── evidence-grounded diagnosis g_t
                 ├── Repair Brief (g_t, π(1)) → candidate 1
                 ├── Repair Brief (g_t, π(2)) → candidate 2
                 ├── ...
                 └── Repair Brief (g_t, π(N)) → candidate N
                      └── targeted screen → Top-K full evaluation
                           └── evolution record → s_(t+1) or retain s_t
```

The evaluator preserves task outcomes and case IDs. The analyzer freezes one shared diagnosis but does not edit the skill. The mutator diversifies candidate strategies, writes one eight-module Repair Brief per candidate, copies the incumbent, and applies bounded edits. The orchestrator performs direction-aware screening and enforces full-set improvement, completion, case-level regression, and slice-level regression gates. The acceptance template provides a readable view of the machine-generated Evolution Record.

## Stable core and benchmark adapters

`src/skillboost/`, `schemas/`, and the three evolution skills define the reusable method. Files under `benchmarks/`, `experiments/`, and `analysis/` are research adapters tied to particular tasks and providers; they may require additional packages or environment setup.

## Compatibility

The deterministic core accepts both the public report schema and several legacy report fields used by the original experiments. New adapters should emit the public schema so correct, incorrect, and undecided case sets remain available for verified acceptance.
