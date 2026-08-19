# Reproducibility

## Offline checks

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
python3 -m skillboost.evolve --help
python3 -m skillboost.orchestrate --help
```

## Paper defaults

| Component | Setting |
|---|---|
| Candidate pool | Best-of-4; 2/6/8 used for ablations |
| Full-evaluation finalists | Top-2 |
| Guard samples | 10-20 incumbent-correct cases |
| Decoding temperature | 0.1 |
| Maximum output tokens | 16,384 |
| Thinking mode | Disabled |
| Environment seed | 42 for ALFWorld |
| API retries | 5 with exponential backoff |

Task-specific limits for interaction steps, code generation, timeouts, and concurrency are recorded in the paper appendix and benchmark scripts.

## Provider control

For DashScope-backed task rollouts, set `SKILLBOOST_LLM_PROVIDER=dashscope` and `DASHSCOPE_API_KEY`; optionally set `DASHSCOPE_BASE_URL` for a region- or workspace-specific OpenAI-compatible endpoint. The same repository-local adapter is used across benchmark families. The provider model performs task rollout and scoring only; it is not the evolution model.

For native Anthropic rollouts, set `SKILLBOOST_LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and `SKILLBOOST_MODEL`; optionally set `ANTHROPIC_BASE_URL`. Record the resolved model ID with every run.

BFCL additionally requires the declared `bfcl` extra. Its code and BFCL-v4 data are resolved from the pinned official `bfcl-eval` package, so a local upstream source tree and `BFCL_PROJECT_ROOT` are not part of the reproduction contract.

## Reproducing an evolution round

1. Freeze the model, dataset split, seed skill, evaluator, and decoding configuration.
2. Run the incumbent skill and retain one trajectory per case.
3. Normalize the run into an evaluation report with correct, incorrect, and undecided case IDs.
4. Run `skillboost.evolve` with Claude Code, or prepare its prompt for an interactive Codex/Claude Code session, to freeze one evidence-grounded Shared Diagnosis and generate \(N\) diversified strategies with one eight-module Repair Brief per candidate. The evolution model does not replace the frozen task model used by the evaluator.
5. Copy the incumbent into one immutable directory per candidate and apply bounded edits.
6. Screen all candidates on the fixed failure set plus guard samples.
7. Fully evaluate the top two candidates.
8. Accept only a positive-gain candidate whose case regression is below the declared threshold; otherwise retain the incumbent.
9. Complete the Repair Brief back-testing modules and store the Verified Acceptance/Evolution Record with all rejected candidates.

## Reporting

Report the model and dataset revisions, number of rounds, candidate count, selection thresholds, development and held-out metrics, case-level regressions, skill length, and token cost. Development failures used for candidate generation are not held-out evidence.

## Credentials and privacy

Provider credentials must be read at runtime from the environment or an external secret manager. Do not commit credential values, request logs, raw sensitive traces, local absolute paths, emails, usernames, or machine metadata. Before release, run the repository's sensitive-information scan described in the project tests and inspect any newly added binary assets separately.
