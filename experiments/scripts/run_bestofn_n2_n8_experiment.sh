#!/bin/bash

set -e

PY="python"
MODEL="qwen3.7-max"
MAX_CONCURRENT=30

PROJECT_ROOT="/path/to/project"
ALFWORLD_DATA="$PROJECT_ROOT/data/alfworld/train.jsonl"
LIVEMATH_DATA="$PROJECT_ROOT/data/livemath/train.jsonl"

ALFWORLD_BASELINE="$PROJECT_ROOT/evolved/alfworld-solver-qwen37max/train_run_20260605_110504/evals/report_train_20260605_110504.json"
LIVEMATH_BASELINE="$PROJECT_ROOT/evolved/livemath-solver-qwen37max/train_run_20260607_152745/evals/report_train_20260607_152745.json"

ALFWORLD_OUTPUT="$PROJECT_ROOT/evolved/alfworld-solver-qwen37max/_bestofn_n8"
LIVEMATH_OUTPUT="$PROJECT_ROOT/evolved/livemath-solver-qwen37max/_bestofn_n8"

echo "======================================================================"
echo "prepare  N=8 candidatedirectory"
echo "======================================================================"

ALFWORLD_CANDS="$PROJECT_ROOT/evolved/alfworld-solver-qwen37max/candidates_n8"
mkdir -p "$ALFWORLD_CANDS"

for c in c1 c2 m1 m2 n1 n2 n3; do
    if [ -f "$PROJECT_ROOT/evolved/alfworld-solver-qwen37max/candidates_v1/$c/SKILL.md" ]; then
        mkdir -p "$ALFWORLD_CANDS/$c"
        cp "$PROJECT_ROOT/evolved/alfworld-solver-qwen37max/candidates_v1/$c/SKILL.md" "$ALFWORLD_CANDS/$c/"
        echo "  ✓ ALFWorld $c (from qwen37max)"
    fi
done

mkdir -p "$ALFWORLD_CANDS/c3_n6"
cp "$PROJECT_ROOT/evolved/alfworld-solver/candidates_n6/c3/SKILL.md" "$ALFWORLD_CANDS/c3_n6/"
echo "  ✓ ALFWorld c3_n6 (from alfworld-solver/candidates_n6)"

echo ""
echo "ALFWorld candidate count: $(ls -d $ALFWORLD_CANDS/*/ 2>/dev/null | wc -l)"

LIVEMATH_CANDS="$PROJECT_ROOT/evolved/livemath-solver-qwen37max/candidates_n8"
mkdir -p "$LIVEMATH_CANDS"

for c in c1 c2 c3 c4 c5 c6; do
    if [ -f "$PROJECT_ROOT/evolved/livemath-solver-qwen36plus/candidates_n6/$c/SKILL.md" ]; then
        mkdir -p "$LIVEMATH_CANDS/$c"
        cp "$PROJECT_ROOT/evolved/livemath-solver-qwen36plus/candidates_n6/$c/SKILL.md" "$LIVEMATH_CANDS/$c/"
        echo "  ✓ LiveMath $c (from candidates_n6)"
    fi
done

mkdir -p "$LIVEMATH_CANDS/c7"
cp "$PROJECT_ROOT/evolved/livemath-solver-qwen36plus/candidates_v2/c1/SKILL.md" "$LIVEMATH_CANDS/c7/"
echo "  ✓ LiveMath c7 (from candidates_v2/c1)"

mkdir -p "$LIVEMATH_CANDS/c8"
cp "$PROJECT_ROOT/evolved/livemath-solver-qwen36plus/candidates_v2/c2/SKILL.md" "$LIVEMATH_CANDS/c8/"
echo "  ✓ LiveMath c8 (from candidates_v2/c2)"

echo ""
echo "LiveMath candidate count: $(ls -d $LIVEMATH_CANDS/*/ 2>/dev/null | wc -l)"

echo ""
echo "======================================================================"
echo "candidateprepare done"
echo "======================================================================"
echo ""
echo "ALFWorld candidate: $(ls $ALFWORLD_CANDS)"
echo "LiveMath candidate: $(ls $LIVEMATH_CANDS)"
echo ""
echo "next step: run  run_bestofn_n8_eval.sh exec  linesevaluation"
