#!/bin/bash

set -e

PY="python"
MODEL="qwen3.7-max"
MAX_CONCURRENT=30

PROJECT_ROOT="/path/to/project"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "ALFWorld Best-of-N N=8 experiment (qwen3.7-max)"
echo "======================================================================"

ALFWORLD_DATA="data/alfworld/train.jsonl"
ALFWORLD_BASELINE="evolved/alfworld-solver-qwen37max/train_run_20260605_110504/evals/report_train_20260605_110504.json"
ALFWORLD_CANDS="evolved/alfworld-solver-qwen37max/candidates_n8"
ALFWORLD_OUTPUT="evolved/alfworld-solver-qwen37max/_bestofn_n8"

ALFWORLD_CANDIDATES=""
for c in c1 c2 m1 m2 n1 n2 n3 c3_n6; do
    if [ -d "$ALFWORLD_CANDS/$c" ]; then
        ALFWORLD_CANDIDATES="$ALFWORLD_CANDIDATES $ALFWORLD_CANDS/$c"
    fi
done

echo "candidate: $ALFWORLD_CANDIDATES"
echo ""

$PY -m skillboost.orchestrate \
    --eval-script benchmarks/evaluators/test_alfworld.py \
    --data "$ALFWORLD_DATA" \
    --baseline-report "$ALFWORLD_BASELINE" \
    --candidates $ALFWORLD_CANDIDATES \
    --topk 2 \
    --output-base "$ALFWORLD_OUTPUT" \
    --max-concurrent $MAX_CONCURRENT \
    --baseline-version v0 \
    --target-version v1_n8 \
    --task-line alfworld-solver-qwen37max \
    --metric-key success_rate \
    --correct-key won_count \
    --fail-ids-key fail_ids \
    --concurrency-arg="--workers" \
    --per-group-key type_success_rate \
    --candidate-subdir "" \
    --eval-extra-args "--model $MODEL --max-steps 50"

echo ""
echo "======================================================================"
echo "ALFWorld N=8 experimentdone"
echo "======================================================================"

echo ""
echo "======================================================================"
echo "LiveMath Best-of-N N=8 experiment (qwen3.7-max)"
echo "======================================================================"

LIVEMATH_DATA="data/livemath/train.jsonl"
LIVEMATH_BASELINE="evolved/livemath-solver-qwen37max/train_run_20260607_152745/evals/report_train_20260607_152745.json"
LIVEMATH_CANDS="evolved/livemath-solver-qwen37max/candidates_n8"
LIVEMATH_OUTPUT="evolved/livemath-solver-qwen37max/_bestofn_n8"

LIVEMATH_CANDIDATES=""
for c in c1 c2 c3 c4 c5 c6 c7 c8; do
    if [ -d "$LIVEMATH_CANDS/$c" ]; then
        LIVEMATH_CANDIDATES="$LIVEMATH_CANDIDATES $LIVEMATH_CANDS/$c"
    fi
done

echo "candidate: $LIVEMATH_CANDIDATES"
echo ""

$PY -m skillboost.orchestrate \
    --eval-script benchmarks/evaluators/test_livemath.py \
    --data "$LIVEMATH_DATA" \
    --baseline-report "$LIVEMATH_BASELINE" \
    --candidates $LIVEMATH_CANDIDATES \
    --topk 2 \
    --output-base "$LIVEMATH_OUTPUT" \
    --max-concurrent $MAX_CONCURRENT \
    --baseline-version v0 \
    --target-version v1_n8 \
    --task-line livemath-solver-qwen37max \
    --metric-key accuracy \
    --correct-key correct \
    --fail-ids-key wrong_ids \
    --concurrency-arg="--max-concurrent" \
    --per-group-key type_accuracy \
    --candidate-subdir "" \
    --eval-extra-args "--model $MODEL"

echo ""
echo "======================================================================"
echo "LiveMath N=8 experimentdone"
echo "======================================================================"
echo ""
echo "resultsview:"
echo "  ALFWorld: cat $ALFWORLD_OUTPUT/selection_report.json"
echo "  LiveMath: cat $LIVEMATH_OUTPUT/selection_report.json"
