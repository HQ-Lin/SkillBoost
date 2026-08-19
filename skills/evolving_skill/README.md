# Generic evolving-skill workflow

This package is the public, domain-independent counterpart of the reference `.qoder/skills/evolving_skill` loop. It preserves the same operational backbone—evaluate, attribute, mutate, back-test, and archive—while adding the paper's Shared Diagnosis, Best-of-\(N\) exploration, and verified acceptance contracts.

## Stage contract

| Stage | Core action | Required outputs |
|---|---|---|
| `skillboost-evaluator` | Execute or ingest a frozen skill run, retain one trace state per case, and compute comparable metrics | `traces/trace_<case-id>.json`, `evals/results_<run>.jsonl`, `evals/report_<run>.json` |
| `skillboost-analyzer` | Prepare evidence, replay failed trajectories, locate causal instruction defects, and freeze the round diagnosis | `attribution-context.md`, `diagnosis.md`, `diagnosis.json` |
| `skillboost-mutator` | Diversify repair strategies, copy the incumbent, apply bounded edits, validate, back-test, select, and archive | candidate directories, Repair Briefs, validation reports, candidate evaluation reports, acceptance/evolution record, promoted version, changelog |

The stage names differ from the reference package only to reflect the paper terminology. `skillboost-mutator` subsumes the reference generator and adds multi-candidate selection.

## End-to-end artifact flow

```text
dataset + frozen skill + execution configuration
  → traces/
  → results.jsonl + evaluation report
  → attribution context
  → Shared Diagnosis g_t
  → N Repair Strategies π(n)
  → N Repair Briefs b_t^(n)
  → N copied-and-edited candidate skill directories
  → candidate-validation.json per candidate
  → fixed-failure-set back-tests
  → Top-K full evaluations
  → Verified Acceptance / Evolution Record
  → promoted version + version manifest + independent changelog
```

## Genericity boundary

The three core skills define artifact and decision protocols only. Benchmark-specific parsers, scoring rules, tools, prompts, datasets, provider clients, and task knowledge belong under `benchmarks/`, `experiments/`, or the task skill being evolved. They must not be embedded in this package.

Concrete execution belongs to a benchmark evaluator or another task adapter that emits the evaluator's generic trace and report contract. Provider APIs, Claude Code, Codex, and interactive environments are interchangeable rollout backends at that adapter boundary; the evolution skills do not depend on a particular vendor harness.

After a baseline report exists, `python3 -m skillboost.evolve` is the optional execution adapter for the analyzer and mutator stages. Its Claude Code mode runs the evolution model without calling the benchmark provider; `prepare-only` mode emits the same portable prompt and candidate workspace for execution in an existing Codex or Claude Code session. Candidate evaluation remains a separate evaluator/orchestrator stage so the task model and its configuration stay frozen.

## Non-negotiable invariants

1. Raw traces remain the evidence source; interrupted runs preserve completed traces and mark absent cases as missing.
2. The analyzer prepares deterministic evidence but does not silently invent causal labels or edit the skill.
3. New candidates are copied from the incumbent and edited locally; the incumbent and previous versions remain immutable.
4. Every back-test uses the complete frozen baseline failed/undecided set, optionally with a deterministic correct-case guard sample.
5. A directed back-test ranks candidates but cannot authorize promotion; finalists require comparable full-set evaluation.
6. A candidate is promoted only after all predeclared improvement, regression, completion, structural, and budget gates pass.
7. Every terminal round retains rejected-candidate evidence and emits an explicit decision record; promotion additionally emits a version manifest and independent changelog.
