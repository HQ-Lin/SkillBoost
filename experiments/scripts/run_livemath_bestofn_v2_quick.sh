#!/bin/bash

set -e

PY="python"
BASE="evolved/livemath-solver-qwen36plus"
MODEL="qwen3.6-plus"
DATA="data/livemath/train.jsonl"
EVAL_SCRIPT="benchmarks/evaluators/test_livemath.py"
MAX_CONCURRENT=50
SAMPLE_RATIO=30  # only run  30% data

echo "======================================================================"
echo "LiveMath Best-of-N v2 ablation experiment (30% dataquick validation) "
echo "======================================================================"
echo ""

V1_REPORT=$(ls -t $BASE/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)
echo "✅ v1 baseline: $V1_REPORT"

CANDS_DIR="$BASE/candidates_v2"

echo ""
echo "══════════════════════════════════════════════════════"
echo "Phase A: directed coarse screening (30% failedsetsamples) "
echo "══════════════════════════════════════════════════════"

FAIL_IDS=$(python3 -c "
import json
report = json.load(open('$V1_REPORT'))
fail_ids = report.get('wrong_ids', [])
import random
random.seed(42)
sample_size = max(1, int(len(fail_ids) * 0.3))
sampled = random.sample(fail_ids, sample_size)
print(' '.join(sampled))
")

echo "📊 v1 failedsettotal: $(python3 -c "import json; print(len(json.load(open('$V1_REPORT')).get('wrong_ids', [])))")"
echo "📊 Phase A sample count (30%) : $(echo $FAIL_IDS | wc -w)"
echo ""

declare -A PHASE_A_SCORES

for cand in c1 c2 c3 c4; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "evaluate candidate: $cand"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    $PY $EVAL_SCRIPT \
        --data $DATA \
        --skill $CANDS_DIR/$cand \
        --max-concurrent $MAX_CONCURRENT \
        --output-base $BASE/_bestofn_v2_quick/${cand}_phase_a \
        --model $MODEL \
        --filter-ids $FAIL_IDS
    
    REPORT=$(ls -t $BASE/_bestofn_v2_quick/${cand}_phase_a/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)
    ACC=$(python3 -c "import json; print(json.load(open('$REPORT'))['accuracy'])")
    PHASE_A_SCORES[$cand]=$ACC
    
    echo "✅ $cand Phase A accuracy: ${ACC}%"
    echo ""
done

echo "══════════════════════════════════════════════════════"
echo "Phase A resultsranking (30% failure set):"
echo "══════════════════════════════════════════════════════"

for cand in c1 c2 c3 c4; do
    echo "  $cand: ${PHASE_A_SCORES[$cand]}%"
done | sort -t: -k2 -rn

TOP2=$(for cand in c1 c2 c3 c4; do echo "${PHASE_A_SCORES[$cand]} $cand"; done | sort -rn | head -2 | awk '{print $2}')
echo ""
echo "🏆 Top-2 entering  Phase B: $TOP2"

echo ""
echo "══════════════════════════════════════════════════════"
echo "Phase B: full-set selection (30% full setsamples) "
echo "══════════════════════════════════════════════════════"

ALL_IDS=$(python3 -c "
import json
data = [json.loads(line) for line in open('$DATA')]
import random
random.seed(42)
sample_size = max(1, int(len(data) * 0.3))
sampled = random.sample(data, sample_size)
for item in sampled:
    print(item['task_id'])
")

echo "📊 full setdatatotal: 35"
echo "📊 Phase B sample count (30%) : $(echo "$ALL_IDS" | wc -l)"
echo ""

declare -A PHASE_B_SCORES

for cand in $TOP2; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "evaluate candidate: $cand (Phase B)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    $PY $EVAL_SCRIPT \
        --data $DATA \
        --skill $CANDS_DIR/$cand \
        --max-concurrent $MAX_CONCURRENT \
        --output-base $BASE/_bestofn_v2_quick/${cand}_phase_b \
        --model $MODEL \
        --filter-ids $ALL_IDS
    
    REPORT=$(ls -t $BASE/_bestofn_v2_quick/${cand}_phase_b/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)
    ACC=$(python3 -c "import json; print(json.load(open('$REPORT'))['accuracy'])")
    PHASE_B_SCORES[$cand]=$ACC
    
    echo "✅ $cand Phase B accuracy: ${ACC}%"
    echo ""
done

echo "======================================================================"
echo "📊 Best-of-N v2 ablation experimentresultssummary (30% data)"
echo "======================================================================"
echo ""
echo "Baseline (v1): 65.7% (full set 35 questions)"
echo ""
echo "Phase A (30% failure set):"
for cand in c1 c2 c3 c4; do
    echo "  $cand: ${PHASE_A_SCORES[$cand]}%"
done
echo ""
echo "Phase B (30% full set):"
for cand in $TOP2; do
    echo "  $cand: ${PHASE_B_SCORES[$cand]}%"
done
echo ""

WINNER=$(for cand in $TOP2; do echo "${PHASE_B_SCORES[$cand]} $cand"; done | sort -rn | head -1 | awk '{print $2}')
WINNER_ACC=${PHASE_B_SCORES[$WINNER]}

echo "🏆 Winner: $WINNER (${WINNER_ACC}%)"
echo ""
echo "💾 detailed reportsave at : $BASE/_bestofn_v2_quick/"
echo "======================================================================"
