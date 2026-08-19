#!/bin/bash

set -e

MODEL="qwen3.7-max"
WORKERS=3
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "formatshufflecomparisonexperiment"
echo "model: $MODEL"
echo "concurrency: $WORKERS"
echo "time: $TIMESTAMP"
echo "=========================================="

LOG_DIR="logs/format_scramble_experiment_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo ""
echo "start concurrencyevaluation4 dataset..."
echo ""

echo "[1/8] BFCL-v4 structuredversion (v4)..."
nohup conda run -n evolution python benchmarks/evaluators/test_bfcl_official.py \
    --skill evolved/bfcl-solver/v4/SKILL.md \
    --concurrency $WORKERS \
    --run_id "v4_structured" \
    --output_dir evolved/bfcl-solver/evals \
    --model $MODEL \
    --category multi_turn_base \
    --limit 0 \
    > "$LOG_DIR/bfcl_v4_structured.log" 2>&1 &
PID1=$!

echo "[2/8] BFCL-v4 shuffleversion (v4_scrambled)..."
nohup conda run -n evolution python benchmarks/evaluators/test_bfcl_official.py \
    --skill evolved/bfcl-solver/v4_scrambled/SKILL.md \
    --concurrency $WORKERS \
    --run_id "v4_scrambled" \
    --output_dir evolved/bfcl-solver/evals \
    --model $MODEL \
    --category multi_turn_base \
    --limit 0 \
    > "$LOG_DIR/bfcl_v4_scrambled.log" 2>&1 &
PID2=$!

echo "[3/8] LiveMath structuredversion (v2)..."
nohup conda run -n evolution python benchmarks/evaluators/test_livemath.py \
    --data data/livemath/test.jsonl \
    --skill evolved/livemath-solver/v2 \
    --max-concurrent $WORKERS \
    --model $MODEL \
    --output-base evolved/livemath-solver/evals_livemath_structured \
    > "$LOG_DIR/livemath_v2_structured.log" 2>&1 &
PID3=$!

echo "[4/8] LiveMath shuffleversion (v2_scrambled)..."
nohup conda run -n evolution python benchmarks/evaluators/test_livemath.py \
    --data data/livemath/test.jsonl \
    --skill evolved/livemath-solver/v2_scrambled \
    --max-concurrent $WORKERS \
    --model $MODEL \
    --output-base evolved/livemath-solver/evals_livemath_scrambled \
    > "$LOG_DIR/livemath_v2_scrambled.log" 2>&1 &
PID4=$!

echo "[5/8] SpreadsheetBench structuredversion (v4)..."
nohup conda run -n evolution python benchmarks/evaluators/test_spreadsheetbench.py \
    --skill evolved/spreadsheetbench-solver/v4 \
    --max-concurrent $WORKERS \
    --model $MODEL \
    --output-base evolved/spreadsheetbench-solver/evals \
    > "$LOG_DIR/spreadsheetbench_v4_structured.log" 2>&1 &
PID5=$!

echo "[6/8] SpreadsheetBench shuffleversion (v4_scrambled)..."
nohup conda run -n evolution python benchmarks/evaluators/test_spreadsheetbench.py \
    --skill evolved/spreadsheetbench-solver/v4_scrambled \
    --max-concurrent $WORKERS \
    --model $MODEL \
    --output-base evolved/spreadsheetbench-solver/evals \
    > "$LOG_DIR/spreadsheetbench_v4_scrambled.log" 2>&1 &
PID6=$!

echo "[7/8] ALFWorld structuredversion (v3_plainVersion)..."
nohup conda run -n evolution python benchmarks/evaluators/test_alfworld.py \
    --data data/alfworld/test.jsonl \
    --skill evolved/alfworld-solver/v3_plainVersion \
    --workers $WORKERS \
    --model $MODEL \
    --executor thread \
    --output-base evolved/alfworld-solver/evals_alfworld_structured \
    > "$LOG_DIR/alfworld_v3_structured.log" 2>&1 &
PID7=$!

echo "[8/8] ALFWorld shuffleversion (v3_scrambled)..."
nohup conda run -n evolution python benchmarks/evaluators/test_alfworld.py \
    --data data/alfworld/test.jsonl \
    --skill evolved/alfworld-solver/v3_scrambled \
    --workers $WORKERS \
    --model $MODEL \
    --executor thread \
    --output-base evolved/alfworld-solver/evals_alfworld_scrambled \
    > "$LOG_DIR/alfworld_v3_scrambled.log" 2>&1 &
PID8=$!

echo ""
echo "=========================================="
echo "all8 evaluationstask (after run ) "
echo "=========================================="
echo "PIDcolumntable:"
echo "  BFCL v4 structured:    $PID1"
echo "  BFCL v4 scrambled:     $PID2"
echo "  LiveMath v2 structured: $PID3"
echo "  LiveMath v2 scrambled:  $PID4"
echo "  SpreadsheetBench v4 structured: $PID5"
echo "  SpreadsheetBench v4 scrambled:  $PID6"
echo "  ALFWorld v3 structured: $PID7"
echo "  ALFWorld v3 scrambled:  $PID8"
echo ""
echo "directory: $LOG_DIR"
echo ""
echo ":"
echo "  tail -f $LOG_DIR/bfcl_v4_structured.log"
echo "  tail -f $LOG_DIR/livemath_v2_structured.log"
echo "  ..."
echo ""
echo "waitingalltaskdone..."

wait $PID1 $PID2 $PID3 $PID4 $PID5 $PID6 $PID7 $PID8

echo ""
echo "=========================================="
echo "allevaluationtaskdone！"
echo "=========================================="
echo ""
echo "resultssummary: "
echo ""

echo "BFCL-v4:"
echo "  structuredversion:"
grep -E "accuracy|Accuracy|ACC" "$LOG_DIR/bfcl_v4_structured.log" | tail -1 || echo "    (not found:results)"
echo "  shuffleversion:"
grep -E "accuracy|Accuracy|ACC" "$LOG_DIR/bfcl_v4_scrambled.log" | tail -1 || echo "    (not found:results)"

echo ""
echo "LiveMath:"
echo "  structuredversion:"
grep -E "accuracy|Accuracy|correct rate|acc" "$LOG_DIR/livemath_v2_structured.log" | tail -1 || echo "    (not found:results)"
echo "  shuffleversion:"
grep -E "accuracy|Accuracy|correct rate|acc" "$LOG_DIR/livemath_v2_scrambled.log" | tail -1 || echo "    (not found:results)"

echo ""
echo "SpreadsheetBench:"
echo "  structuredversion:"
grep -E "accuracy|Accuracy|acc" "$LOG_DIR/spreadsheetbench_v4_structured.log" | tail -1 || echo "    (not found:results)"
echo "  shuffleversion:"
grep -E "accuracy|Accuracy|acc" "$LOG_DIR/spreadsheetbench_v4_scrambled.log" | tail -1 || echo "    (not found:results)"

echo ""
echo "ALFWorld:"
echo "  structuredversion:"
grep -E "accuracy|Accuracy|acc|success" "$LOG_DIR/alfworld_v3_structured.log" | tail -1 || echo "    (not found:results)"
echo "  shuffleversion:"
grep -E "accuracy|Accuracy|acc|success" "$LOG_DIR/alfworld_v3_scrambled.log" | tail -1 || echo "    (not found:results)"

echo ""
echo "=========================================="
echo "experimentdone！detailed save at : $LOG_DIR"
echo "=========================================="
