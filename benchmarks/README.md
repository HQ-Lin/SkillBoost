# Benchmarks

This directory contains the empirical task runners used during SkillBoost development. The scripts under `evaluators/` are the concrete execution entry points, despite their historical `test_*.py` names.

- `evaluators/` loads a frozen task skill, launches task- and provider-specific executions, captures per-case trajectories, scores outcomes, and writes results and reports.
- `dataset_builders/` converts upstream datasets into local JSONL inputs.

An evaluator therefore combines four benchmark-specific responsibilities: rollout harness, task/environment adapter, output parser, and scorer. The reusable self-evolution loop consumes its artifacts; it does not replace the evaluator with a second top-level harness.

These adapters are supporting research code, not the method's stable API. Several require benchmark-specific packages, external datasets, model-provider credentials, or licensed environments. Review each script before use and normalize its output to `schemas/evaluation-report.schema.json` before cross-benchmark selection.

Current task families include interactive environments, function calling, document QA, mathematical reasoning, office QA, search QA, spreadsheets, and software engineering. Their scores are not directly comparable; comparisons should be made within a fixed task, split, model, and execution configuration.

## Model provider

All OpenAI-compatible evaluator paths use `evaluators/provider.py`.

```bash
export SKILLBOOST_LLM_PROVIDER=dashscope
export DASHSCOPE_API_KEY="<read from your secret manager>"
# export DASHSCOPE_BASE_URL="<regional or workspace base URL ending in /v1>"
```

If `SKILLBOOST_LLM_PROVIDER` is omitted, the presence of `DASHSCOPE_API_KEY` selects DashScope. A non-DashScope endpoint requires `SKILLBOOST_LLM_PROVIDER=openai-compatible`, `LLM_API_KEY`, and `LLM_BASE_URL`. Credentials are never accepted as evaluator command-line arguments.

For the native Anthropic backend, set `SKILLBOOST_LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and `SKILLBOOST_MODEL`; `ANTHROPIC_BASE_URL` is optional. The shared adapter translates system prompts, multimodal image blocks, tool definitions, accumulated assistant tool calls, and tool results to the Messages API while preserving each evaluator's existing trajectory format.

## BFCL

Install the project-declared official runtime with `python3 -m pip install -e '.[bfcl]'`. The BFCL adapters resolve benchmark data from the installed `bfcl_eval` package; no separate Gorilla/SkillLens checkout or path configuration is required. `--bfcl-data-dir` can override packaged data for a controlled dataset snapshot.
