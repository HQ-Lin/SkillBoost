---
name: skillboost-analyzer
description: Attribute agent-skill failures from evaluation records and raw trajectories, then produce the shared evidence-grounded diagnosis for a SkillBoost evolution round. Use after a valid evaluation and before candidate repair strategies are proposed; do not edit the skill or treat infrastructure failures as strategy defects.
---

# SkillBoost Analyzer

Convert observed failures into the shared diagnosis \(g_t\) used by every candidate in one evolution round. The unit of analysis is the earliest causal decision error, not the final wrong answer.

## Preconditions

Require the incumbent `SKILL.md`, a valid evaluation report, case records, and raw traces for the cases under analysis. If trace completeness is below the declared threshold, pause attribution and request a rerun.

## Stage outputs

Produce two distinct artifacts and do not collapse them:

1. `attribution-context.md`: deterministic evidence preparation containing the run snapshot, incumbent section index, failed/undecided case packets, optional version trend, regression alerts, and prior repair summaries.
2. `diagnosis.md` plus `diagnosis.json`: the agent-authored Shared Diagnosis \(g_t\), conforming to `schemas/diagnosis.schema.json`.

The context is evidence, not a causal conclusion. The diagnosis is the reviewed causal artifact handed to candidate generation.

## Procedure

1. Run `scripts/prepare_context.py` to assemble deterministic evidence packets. Supply earlier reports and Repair Briefs when available so version trends, recurring failures, and regressions are visible.
2. Quarantine `engineering_anomaly` and `label_issue` cases before strategy analysis.
3. Replay each remaining trajectory from input to output. Mark the earliest decision that diverges from the desired process.
4. Locate the incumbent instruction that is missing, ambiguous, overbroad, misordered, or unreachable.
5. Cluster cases only when they share the same causal mechanism and repair location.
6. For each cluster, record evidence, causal error, incumbent location, counterfactual condition, competing hypothesis, confidence, and disposition.
7. Freeze the failed/undecided screening IDs, protected slices, and candidate-independent constraints.
8. Emit one Shared Diagnosis conforming to `schemas/diagnosis.schema.json`.

## Deterministic helper

Prepare the evidence context without invoking a model:

```bash
python3 scripts/prepare_context.py \
  <run-dir>/evals/report_<run>.json \
  <run-dir>/evals/results_<run>.jsonl \
  <incumbent>/SKILL.md \
  --history-report <earlier-report.json> \
  --prior-brief <earlier-repair-brief.md> \
  --output <round-dir>/attribution-context.md
```

Repeat the history options as needed in chronological order. Omit them on the first round.

Read [references/attribution-guide.md](references/attribution-guide.md) when distinguishing strategy defects from capability gaps. Use [references/diagnosis-template.md](references/diagnosis-template.md) when writing the round artifact.

## Evidence standard

A repair item is admissible only when it contains the full chain:

```text
case IDs -> trace evidence -> earliest causal error
         -> incumbent skill location -> counterfactual condition -> resolution test
```

Counterfactual test: if the proposed instruction had been present and followed, would it likely have prevented the cited error without prescribing the ground-truth answer? If not, revise or reject the hypothesis.

## Invariants

- Do not infer reasoning from the final answer when a trajectory is available.
- Do not cluster by topic or lexical similarity alone.
- Do not write benchmark answers, case IDs, or narrow answer patterns into a general skill.
- Repeated non-response to well-targeted edits is evidence for `capability_gap`, not justification for more prose.
- References that the incumbent never loads are reachability defects, not missing knowledge.
- Keep alternative causal hypotheses separate when evidence does not discriminate them.
- Do not choose edit scope or candidate priority here; those define \(\pi^{(n)}\) and belong to the Mutator.
- Every Repair Brief in the same round must reference the same immutable diagnosis ID and content.

## Handoff

Return the attribution context, Shared Diagnosis in Markdown and JSON, quarantined cases, unresolved hypotheses, and the fixed set of baseline failed/undecided case IDs. Do not propose a candidate strategy or create a new skill version—the Mutator owns those transitions.
