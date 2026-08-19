---
name: skillboost-mutator
description: Diversify paper-aligned Repair Briefs from a shared SkillBoost diagnosis, then create and validate bounded candidate mutations of a versioned task skill. Use after causal attribution is complete; do not mutate for engineering anomalies, disputed labels, or unsupported hypotheses.
---

# SkillBoost Mutator

Pair the shared diagnosis \(g_t\) with candidate-specific strategies \(\pi^{(n)}\), then turn each Repair Brief \(b_t^{(n)}=(g_t,\pi^{(n)})\) into a reviewable candidate diff. Preserve ancestry, vary hypotheses rather than wording, and never self-approve a candidate.

## Preconditions

Require an incumbent skill, a valid Shared Diagnosis, mutation budget, evaluation adapter, and promotion policy. Process only clusters whose disposition is `repair` or `decompose`.

Stop before mutation when engineering anomalies dominate, labels require adjudication, or the diagnosis lacks trace support. Route capability gaps to decomposition rather than adding unsupported prose.

## Brief construction

1. Freeze the Shared Diagnosis; do not rewrite its evidence or clusters per candidate.
2. Draft \(N\) materially different strategies using [references/repair-strategy-template.md](references/repair-strategy-template.md).
3. Create one eight-module Repair Brief per strategy using [references/repair-brief-template.md](references/repair-brief-template.md); its JSON companion conforms to `schemas/repair-brief.schema.json`.
4. Complete modules 1–6 before editing or evaluation. Leave measured fields in module 7 pending rather than predicting results.
5. Preserve each pre-evaluation brief and append measured back-testing results and execution status after evaluation.

Validate the Markdown artifact at both lifecycle boundaries:

```bash
python3 scripts/validate_repair_brief.py repair-brief.md --stage draft
python3 scripts/validate_repair_brief.py repair-brief.md --stage evaluated
```

## Candidate construction

1. Copy the entire incumbent skill directory into a new candidate directory.
2. Assign each candidate the coherent strategy declared by its Repair Brief.
3. Apply the smallest mutation operator that tests the hypothesis: `ADD`, `REFINE`, `REORDER`, `PRUNE`, or `DECOMPOSE`.
4. Mount any new reference from `SKILL.md`; remove dead or duplicated guidance.
5. Record parent checksum, addressed cluster/action IDs, operator, touched files, expected effect, and regression risk.
6. Run `scripts/validate_candidate.py` against the incumbent and candidate.

Read [references/mutation-operators.md](references/mutation-operators.md) for operator choice and interference controls. Read [references/promotion-policy.md](references/promotion-policy.md) before screening or promotion.

## Population design

When the budget permits multiple candidates, make them scientifically informative:

- candidate A tests the minimal repair;
- candidate B tests a competing causal hypothesis;
- candidate C tests decomposition when the brief indicates a capability boundary.

Do not create nominal variants that differ only in phrasing. Do not combine unrelated repairs merely to increase the chance of improvement.

## Selection

1. Evaluate every candidate on the fixed baseline failed/undecided set, optionally plus a deterministic anti-regression sample.
2. Advance the top `K` candidates by the declared, direction-aware screen metric.
3. Evaluate finalists on the full development set.
4. Apply primary-metric, completion, case-regression, slice-regression, structural, complexity, and cost gates.
5. Promote the best eligible candidate; otherwise retain the incumbent and record rejection reasons.

Use `python3 -m skillboost.orchestrate --help` for deterministic two-stage selection. The directed screen alone can never authorize promotion.

## Back-test and revision loop

If a candidate fails the directed screen, use its new traces for incremental attribution:

1. distinguish an uncorrected original cause from a newly introduced side effect;
2. update only the same candidate and its Repair Brief while it remains unevaluated as an immutable revision;
3. rerun the complete frozen baseline failed/undecided set, never only the cases still failing after the last attempt;
4. stop or decompose after three consecutive non-improving attempts on the same causal cluster.

Every evaluated revision must have a distinct directory or immutable identifier. A successful directed back-test still requires full-set verified acceptance.

## Terminal outputs

Every round returns:

- one strategy and Repair Brief per candidate;
- one copied candidate directory and `candidate-validation.json` per evaluated artifact;
- directed-screen reports for all candidates and full-set reports for finalists;
- a completed acceptance/evolution record containing the winner or explicit rejection reasons;
- all rejected candidates and their evidence.

When promotion succeeds, also create a new immutable version directory, a version manifest, and an independent changelog. Do not put changelog text inside `SKILL.md`, overwrite an incumbent/version, or mark a copied directory as promoted before the acceptance record passes.

## Invariants

- Copy then edit; never regenerate the incumbent from memory.
- One candidate directory corresponds to one immutable evaluated artifact.
- Never overwrite a previous version or evaluation run.
- Never insert case-specific answers or hidden test information.
- New guidance states applicability, non-applicability, and priority when overlap is possible.
- Growth is a cost: prefer a shorter candidate when performance and risk are indistinguishable.
- Three consecutive non-improving repairs to the same causal cluster trigger stop/decompose review.
- Modules 1–3 of all briefs in a round remain diagnosis-equivalent; only strategy and resulting measurements may differ.

## Handoff

Return candidate Repair Briefs, provenance, validation reports, and completed back-testing fields. The Evaluator and orchestrator own verified acceptance; a new directory without a passing acceptance record is not a promoted skill.
