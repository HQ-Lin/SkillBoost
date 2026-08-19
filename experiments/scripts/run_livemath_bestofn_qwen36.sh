#!/bin/bash

set -e

PY="python"
EVAL_SCRIPT="benchmarks/evaluators/test_livemath.py"
DATA="data/livemath/train.jsonl"
BASE="evolved/livemath-solver-qwen36plus"
MODEL="qwen3.6-plus"
MAX_CONCURRENT=50  # highconcurrencyspeedup

echo "======================================================================"
echo "LiveMath Best-of-N experiment (qwen3.6-plus)"
echo "======================================================================"
echo "model: $MODEL"
echo "baseline: $BASE/v0"
echo "concurrency: $MAX_CONCURRENT"
echo ""

V0_REPORT=$(ls -t $BASE/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)

if [ -z "$V0_REPORT" ]; then
    echo "❌ not found: v0 baseline report, run  v0 evaluation..."
    $PY $EVAL_SCRIPT \
        --data $DATA \
        --skill $BASE/v0 \
        --max-concurrent $MAX_CONCURRENT \
        --output-base $BASE \
        --model $MODEL
    V0_REPORT=$(ls -t $BASE/train_run_*/evals/report_train_*.json 2>/dev/null | head -1)
fi

echo "✅ v0 baseline report: $V0_REPORT"
echo ""

CANDS_DIR="$BASE/candidates_v1"
mkdir -p $CANDS_DIR/{c1,c2,c3,c4}

echo "📝 create 4  candidate SKILL.md..."

cat > $CANDS_DIR/c1/SKILL.md << 'EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c1: reinforcequantifiersymbolannotate (∃/∀/↔) "
current_version: v1_c1
parent_version: v0
---



**task definition**: given one high etc countmulti-option questions, select the uniquecorrect optionitemlabel.

**scoring method**: Exact Match, only look at  `<answer>` labelin  optionitemlabel.


1. **full optionitemside-by-side comparisonfor **: read fullyalloptionitemthen decide.
2. **forced quantifier symbol annotation**: for per  optionitemmustuse symbolannotate:
   - ∃ (store at ) / ∀ (any) / ↔ (require ) / → (sufficient)
   - show example: "there exists x" → "∃x"
3. **for for **: similar optionsitemsentence by sentencefor , find out one difference.


1. check weakening (drop  etc/characterize)
2. check over-strong (promotionthen /quantifier)
3.  countdependency verification


1. check for assumed and domain
2.  etc and very valuecase
3. boundary endpoints (/interval)


extractfull assumed, explicitconclusionclasstype.

use symbolannotateper  optionitem quantifier.

excluded weakentype, over-strongtype, assumedtampertype.

confirmassumed, quantifier,  etcfull .


| classtype | avoid |
|------|------|
| quantifier shift | force ∃/∀ annotate |
| wrongly picking an over-strong optionitem | checkassumedsupport |
| lost etc | pick the strongest option that still holds  |
| assumedtamper | per  itemscheck for  |
| premature commit | forced side-by-side comparisonfor  |


`<answer>B</answer>`
EOF

cat > $CANDS_DIR/c2/SKILL.md << 'EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c2: reinforceexcluded  (mustexcluded ≥2 optionitem) "
current_version: v1_c2
parent_version: v0
---



**task definition**: given one high etc countmulti-option questions, select the uniquecorrect optionitemlabel.

**scoring method**: Exact Match, only look at  `<answer>` labelin  optionitemlabel.


1. **full optionitemside-by-side comparisonfor **: read fullyalloptionitemthen decide.
2. **lock quantifier differences**: tracestore at /any/require  etcquantifier.
3. **forceexcluded  (⚠️ key) **: **mustexplicitexcluded to  2  optionitem**,  and write outexcluded , then can answer.
4. **for for **: similar optionsitemsentence by sentencefor .


1. check weakening (drop  etc/characterize)
2. check over-strong (promotionthen /quantifier)
3.  countdependency verification


1. check for assumed and domain
2.  etc and very valuecase
3. boundary endpoints


extractfull assumed, explicitconclusionclasstype.

annotateper  optionitem quantifier and .

**mustexcluded to  2  optionitem**, write outper  excluded  :
- "excluded  A: weakenconclusion (drop  etc) "
- "excluded  C: over-strong ( questionsonly guaranteesstore at , optionitemsay any) "

at candidate in , check is whether  questions.


| classtype | avoid |
|------|------|
| quantifier shift | annotate each quantifier |
| wrongly picking an over-strong optionitem | checkassumedsupport |
| lost etc | pick the strongest option that still holds  |
| assumedtamper | per  itemscheck for  |
| premature commit | **forceexcluded ≥2 optionitem** |


`<answer>B</answer>`
EOF

cat > $CANDS_DIR/c3/SKILL.md << 'EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c3: SOP top  + optionitem"
current_version: v1_c3
parent_version: v0
---



**task definition**: given one high etc countmulti-option questions, select the uniquecorrect optionitemlabel.

**scoring method**: Exact Match, only look at  `<answer>` labelin  optionitemlabel.

**⚠️ optionitem**: like  optionitemto  "one of the remaining options is correct, but a stronger result holds", **optionitem as correctanswer**, directchoose.


scanalloptionitem,  is whether it containswith  "one of the remaining"  or  "stronger result" keyword.
- like  is  → directchooseoptionitem, to  Step 4.
- like whether  → continue Step 2.

extractfull assumed, explicitconclusionclasstype.

- full optionitemside-by-side comparisonfor
- annotate quantifiers (store at /any/require )
- for for similar optionsitem

`<answer>B</answer>`


1. full optionitemside-by-side comparisonfor
2. lock quantifier differences
3. for for


1. check weakening
2. check over-strong
3.  count


1. check for assumed
2.  etccase
3. boundary endpoints


| classtype | avoid |
|------|------|
| optionoptionitem | **Step 1 prefercheck** |
| quantifier shift | annotate each quantifier |
| wrongly picking an over-strong optionitem | checkassumedsupport |
| lost etc | pick the strongest option that still holds  |
| premature commit | forced side-by-side comparisonfor  |


`<answer>B</answer>`
EOF

cat > $CANDS_DIR/c4/SKILL.md << 'EOF'
---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: "c4: rulethen  (single  + output) "
current_version: v1_c4
parent_version: v0
---



**task definition**: given one high etc countmulti-option questions, select the uniquecorrect optionitemlabel.

**scoring method**: Exact Match, only look at  `<answer>` labelin  optionitemlabel.


1. **full optionitemside-by-side comparisonfor **: read fullyalloptionitemthen decide.
2. **lock quantifier differences**: tracestore at /any/require  etcquantifier.
3. **for for **: similar optionsitemsentence by sentencefor , find out one difference.


1. check weakening (drop  etc/characterize)
2. check over-strong (promotionthen /quantifier)
3.  countdependency verification


1. check for assumed and domain
2.  etc and very valuecase
3. boundary endpoints


extractfull assumed, explicitconclusionclasstype.

annotateper  optionitem quantifier and .

excluded weakentype, over-strongtype, assumedtampertype.

**outputtop mustper itemcheck**:
- [ ] quantifier is whether donefull match (∃ vs ∀) ？
- [ ]  etc is whether missed？
- [ ] assumed is whether tampered (interval/dimension/) ？
- [ ]  is whether optionover-strongitem ( questionsnot support) ？
- [ ]  is whether see optionitem？

`<answer>B</answer>`


1. **must**use  `<answer>...</answer>` label
2. labelin **only can **has single  (A/B/C/D/E)
3. **forbidden**, empty,
4. **forbidden**outputmulti-  `<answer>` label

correctshow example:
- `<answer>B</answer>` ✅
- `<answer>B</answer>.` ❌ (multi-)
- `<answer>B </answer>` ❌ (multi-empty)


| classtype | avoid |
|------|------|
| quantifier shift | annotate each quantifier |
| wrongly picking an over-strong optionitem | checkassumedsupport |
| lost etc | pick the strongest option that still holds  |
| assumedtamper | per  itemscheck for  |
| premature commit | forced side-by-side comparisonfor  |
| outputformaterror | **output** |
EOF

echo "✅ 4  candidatecreate: $CANDS_DIR/{c1,c2,c3,c4}"
echo ""

echo "🚀 start  Best-of-N ..."
echo ""

$PY -m skillboost.orchestrate \
    --eval-script $EVAL_SCRIPT \
    --data $DATA \
    --baseline-report $V0_REPORT \
    --candidates $CANDS_DIR/c1 $CANDS_DIR/c2 $CANDS_DIR/c3 $CANDS_DIR/c4 \
    --topk 2 \
    --output-base $BASE/_bestofn_v1 \
    --max-concurrent $MAX_CONCURRENT \
    --baseline-version v0 \
    --target-version v1 \
    --task-line livemath-solver-qwen36plus \
    --metric-key accuracy \
    --correct-key hard_count \
    --fail-ids-key wrong_ids \
    --concurrency-arg=--max-concurrent \
    --candidate-subdir= \
    --eval-extra-args "--model $MODEL"

echo ""
echo "======================================================================"
echo "✅ Best-of-N done！"
echo "======================================================================"
echo "📊 viewreport: $BASE/_bestofn_v1/selection_report.json"
echo ""
echo "next step: "
echo "  1. view selection_report.json confirm winner"
echo "  2. like  winner at  baseline, exec  lines promote: "
echo "     cp -r $BASE/_bestofn_v1/winner $BASE/v1"
echo "======================================================================"
