#!/bin/bash

set -e

PY="python"
MAX_CONCURRENT=50  # highconcurrencyspeedup
LOG_DIR="logs/bestofn_v2_batch"
mkdir -p $LOG_DIR

echo "======================================================================"
echo "multi-dataset Best-of-N v2 batch evolution"
echo "======================================================================"
echo "start time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

run_livemath_bestofn_v2() {
    echo ""
    echo "══════════════════════════════════════════════════════"
    echo "task 1: LiveMath qwen3.6-plus (v1 → v2)"
    echo "baselineaccuracy: 65.7% (train 35 questions)"
    echo "strategy: low baseline, continue Best-of-N exploration"
    echo "══════════════════════════════════════════════════════"
    
    BASE="evolved/livemath-solver-qwen36plus"
    MODEL="qwen3.6-plus"
    DATA="data/livemath/train.jsonl"
    EVAL_SCRIPT="benchmarks/evaluators/test_livemath.py"
    CURRENT_VERSION="v1"
    TARGET_VERSION="v2"
    
    V1_REPORT=$(ls -t $BASE/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)
    if [ -z "$V1_REPORT" ]; then
        echo "❌ not found: v1 baseline report"
        return 1
    fi
    
    echo "✅ v1 baseline: $V1_REPORT"
    
    CANDS_DIR="$BASE/candidates_v2"
    mkdir -p $CANDS_DIR/{c1,c2,c3,c4}
    
    echo "📝 create 4  candidate SKILL.md..."
    
    cat > $CANDS_DIR/c1/SKILL.md << 'SKILL_EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c1: by classtypecustom strategy (Implication/Universal/Existence difference) "
current_version: v2_c1
parent_version: v1
---



**task definition**: given one high etc countmulti-option questions, select the uniquecorrect optionitemlabel.

**scoring method**: Exact Match, only look at  `<answer>` labelin  optionitemlabel.


based on classtypeuse use not same strategy:

- **core**: checktop →conclusion single
- **pitfall**: optionitem"sufficient""require "
- **strategy**: annotate → symbol, verify  is whether can

- **core**: ∀ quantifier use
- **pitfall**: "for all x"weaken as "store at  x"
- **strategy**: forceannotate ∀, checkboundary items

- **core**: ∃ build
- **pitfall**: optionitemname"one store at "but  questionsonly guarantees"store at "
- **strategy**: check is whether multi-out "unique"restricted

- **core**: ↔ with
- **pitfall**: only single
- **strategy**: verify two


1. **full optionitemside-by-side comparisonfor **
2. **forced quantifier symbol annotation** (∃/∀/→/↔)
3. **for for **


judge questionsat  Implication/Universal/Existence/Biconditional  etc.

by # classtypecustom strategyanalysis.

excluded weakentype, over-strongtype, assumedtampertype.

`<answer>B</answer>`


`<answer>B</answer>`
SKILL_EOF

    cat > $CANDS_DIR/c2/SKILL.md << 'SKILL_EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c2: reinforceexamplebuild (noiseitem) "
current_version: v2_c2
parent_version: v1
---



**task definition**: given one high etc countmulti-option questions, select the uniquecorrect optionitemlabel.

**scoring method**: Exact Match, only look at  `<answer>` labelin  optionitemlabel.


for per  optionitem, tryingbuildexample:

1. **weakentypenoiseitem**:
   -  questionssay "require ", optionitemonly say "sufficient"
   - example: find one  sufficientbut not require  case
   
2. **over-strongtypenoiseitem**:
   -  questionsonly guarantees"store at ", optionitemsay "for any"
   - example: find one  store at but not any case

3. **assumedtampertype**:
   -  questionsassumed γ∈[1,8/3), optionitemsay  γ∈[1,∞)
   - example: take  γ=3, verify conclusion is whether


1. full optionitemside-by-side comparisonfor
2. **for per  optionitem: "whetherbuildexample？"**
3. quantifier annotation (∃/∀/→/↔)


extractassumed and conclusion.

for per  optionitem, tryingbuildexample:
- "like option A, whetherfoundone  examplenot ？"
- like can buildexample → excluded
- like not can  → keep


`<answer>B</answer>`


`<answer>B</answer>`
SKILL_EOF

    cat > $CANDS_DIR/c3/SKILL.md << 'SKILL_EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c3: reinforce etc and boundary itemscheck"
current_version: v2_c3
parent_version: v1
---



**task definition**: given one high etc countmulti-option questions, select the uniquecorrect optionitemlabel.

**scoring method**: Exact Match, only look at  `<answer>` labelin  optionitemlabel.


- [ ] not  etc in  etc？
- [ ] optionitem is whether drop  etc (weaken) ？
- [ ] optionitem is whether multi-out  etc (over-strong) ？

- [ ] interval is interval is interval？(a,b) vs [a,b]
- [ ] value is whether it containswith ？
- [ ] dimension items: N=2 vs N=3 vs N≥3

- [ ] max value/min valuewhetherto ？
- [ ] / is whether at set？


1. full optionitemside-by-side comparisonfor
2. **per optionitemcheck etc and boundary**
3. quantifier annotation


extractassumed, domain, boundary items.

for per  optionitem:
-  etc is whether  and  questionsconsistent？
- interval is whether match？
- dimension items is whether correct？


`<answer>B</answer>`


`<answer>B</answer>`
SKILL_EOF

    cat > $CANDS_DIR/c4/SKILL.md << 'SKILL_EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c4: very simple variant (remove, clustercore) "
current_version: v2_c4
parent_version: v1
---



**task**: given high etc countmulti-option questions, select the uniquecorrectoptionitem.

**scoring**: Exact Match, `<answer>B</answer>`


1. **full optionitemside-by-side comparisonfor **: donealloptionitemthen
2. **quantifiertrace**: ∃/∀/→/↔ not can
3. **for for **: similar optionsitemfind one difference


- assumed is ？
- conclusionclasstype (store at /full name/with / etc value) ？

- annotate quantifiers
- checkassumed is whether tampered
- excluded weaken/over-strongitem

`<answer>B</answer>`


| classtype | avoid |
|------|------|
| quantifier shift | annotate ∃/∀ |
| wrongly picking an over-strong optionitem | checkassumedsupport |
| lost etc | pick the strongest option that still holds  |
| premature commit | forced side-by-side comparisonfor  |


`<answer>B</answer>`
SKILL_EOF

    echo "✅ 4  candidatecreate"
    echo ""
    
    echo "🚀 run  Best-of-N v2..."
    
    $PY -m skillboost.orchestrate \
        --eval-script $EVAL_SCRIPT \
        --data $DATA \
        --baseline-report $V1_REPORT \
        --candidates $CANDS_DIR/c1 $CANDS_DIR/c2 $CANDS_DIR/c3 $CANDS_DIR/c4 \
        --topk 2 \
        --output-base $BASE/_bestofn_v2 \
        --max-concurrent $MAX_CONCURRENT \
        --baseline-version v1 \
        --target-version v2 \
        --task-line livemath-solver-qwen36plus \
        --metric-key accuracy \
        --correct-key hard_count \
        --fail-ids-key wrong_ids \
        --concurrency-arg=--max-concurrent \
        --candidate-subdir= \
        --eval-extra-args "--model $MODEL"
    
    echo ""
    echo "✅ LiveMath Best-of-N v2 done！"
    echo "📊 viewreport: $BASE/_bestofn_v2/selection_report.json"
}

run_alfworld_bestofn_v3() {
    echo ""
    echo "══════════════════════════════════════════════════════"
    echo "task 2: ALFWorld qwen3.6-plus (v2 → v3)"
    echo "baselineaccuracy: 97.2% (train 30 questions)"
    echo "⚠️  warning: high baseline, Best-of-N can can valid"
    echo "strategy: tryingbut reportresults, like regressionthen keep v2"
    echo "══════════════════════════════════════════════════════"
    
    BASE="evolved/alfworld-solver"
    MODEL="qwen3.6-plus"
    DATA="data/alfworld/train.jsonl"
    EVAL_SCRIPT="benchmarks/evaluators/test_alfworld.py"
    CURRENT_VERSION="v2"
    TARGET_VERSION="v3"
    
    V2_REPORT=$(ls -t $BASE/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)
    if [ -z "$V2_REPORT" ]; then
        echo "❌ not found: v2 baseline report"
        return 1
    fi
    
    echo "✅ v2 baseline: $V2_REPORT"
    echo ""
    echo "⚠️  ALFWorld  97.2%, continue Best-of-N gainvery low"
    echo "suggestion: keep v2, not continue evolution"
    echo ""
    echo "like requires forcerun , uncomment the following comment"
}

run_docvqa_bestofn_v2() {
    echo ""
    echo "══════════════════════════════════════════════════════"
    echo "task 3: DocVQA qwen3.7-plus (v1 → v2)"
    echo "baselineaccuracy: 90.7% (train 150 questions)"
    echo "⚠️  warning:  in high baseline, requires "
    echo "strategy: run but mustuse  test holdout verify "
    echo "══════════════════════════════════════════════════════"
    
    BASE="evolved/docvqa-solver-qwen37plus"
    MODEL="qwen3.7-plus"
    DATA="data/docvqa/train.jsonl"
    EVAL_SCRIPT="benchmarks/evaluators/test_docvqa.py"
    CURRENT_VERSION="v1"
    TARGET_VERSION="v2"
    
    V1_REPORT=$(ls -t $BASE/_test_v1/evals/report_test_*.json 2>/dev/null | head -1)
    if [ -z "$V1_REPORT" ]; then
        V1_REPORT=$(ls -t $BASE/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)
    fi
    
    if [ -z "$V1_REPORT" ]; then
        echo "❌ not found: v1 baseline report"
        return 1
    fi
    
    echo "✅ v1 baseline: $V1_REPORT"
    echo ""
    echo "⚠️  DocVQA v1  is  test  (90.7%)"
    echo "top  v2 at  train  98% but  test rolled back to  88.7% () "
    echo ""
    echo "suggestion: keep v1, not continue evolution"
    echo ""
    echo "like requires forcerun , uncomment the following comment"
}

echo "chooserequire exec  lines task: "
echo "1. LiveMath v1→v2 (recommended, low baseline)"
echo "2. ALFWorld v2→v3 (not recommended, high baseline)"
echo "3. DocVQA v1→v2 (not recommended, )"
echo "4. full run "
echo ""
read -p "choose [1/2/3/4] (default 1): " choice

case ${choice:-1} in
    1)
        run_livemath_bestofn_v2
        ;;
    2)
        run_alfworld_bestofn_v3
        ;;
    3)
        run_docvqa_bestofn_v2
        ;;
    4)
        run_livemath_bestofn_v2
        run_alfworld_bestofn_v3
        run_docvqa_bestofn_v2
        ;;
    *)
        echo "❌ no validchoose"
        exit 1
        ;;
esac

echo ""
echo "======================================================================"
echo "✅ Best-of-N v2 batch evolutiondone！"
echo "======================================================================"
echo "time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "📊 resultssummary: "
echo "  LiveMath:   evolved/livemath-solver-qwen36plus/_bestofn_v2/selection_report.json"
echo "  ALFWorld:   evolved/alfworld-solver/_bestofn_v3/selection_report.json (like run )"
echo "  DocVQA:     evolved/docvqa-solver-qwen37plus/_bestofn_v2/selection_report.json (like run )"
echo "======================================================================"
