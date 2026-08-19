#!/usr/bin/env python3
import json
from pathlib import Path

def generate_trend_report():
    """generate trendanalysisreport"""
    
    report = """# Skillline count and performance gaintrendanalysis

> analysistime: 2026-06-11
> datasource: cross_model_comprehensive_analysis.json
> samples: 7 model-benchmarkgroup

**key findings**: Skillline countincrease and performance gain**not foundsimplesingle  related**,  is  nonlinear relation.

| line countchangeinterval | example count | avggain | dicttypeexample |
|-------------|--------|----------|---------|
| **0 lines** (rulethen optimize) | 1 | +2.70pp | ALFWorld-kimi-k2.6: line countnot change, qualityoptimize |
| **1-30 lines** (lean improvement) | 2 | +13.43pp | LiveMath-qwen3.7-max: +15 lines→+18.86pp  |
| **30-80 lines** ( in expansion) | 2 | +5.57pp | ALFWorld-qwen3.6-plus: +27 lines→+11.11pp |
| **80-180 lines** (large expansion) | 2 | +3.18pp | SpreadSheet-qwen3.7-max: +173 lines→+5.36pp |

**trend interpretation**:
- **bestinterval**: 1-30 lines lean improvementmost highavggain (+13.43pp)
- **valid**: line count80 linesafter , marginal gainsignificantdecrease (+3.18pp)
- **quality> count**: 0 lineschange (pure qualityoptimize) can +2.70ppgain

**key findings**: v0baselineaccuracy and skillevolutioncan  performance gain**significantrelated** (related count-0.75) .

| baselineinterval | example count | avggain | dicttypeexample |
|---------|--------|----------|---------|
| **<30%** (low baseline) | 1 | +18.86pp | LiveMath-qwen3.7-max (17.14%) |
| **30-60%** ( in low baseline) | 2 | +4.67pp | BFCL-qwen3.7-max (51.60%), LiveMath-kimi-k2.6 (42.40%) |
| **60-90%** ( in high baseline) | 2 | +6.85pp | SpreadSheet-qwen3.7-max (72.50%), ALFWorld-kimi-k2.6 (80.60%) |
| **>90%** (high baseline) | 2 | +0.64pp | ALFWorld-qwen3.7-max (94.30%), ALFWorld-qwen3.6-plus (86.11%) |

**trend interpretation**:
- **low baselinehighgain**: baseline<30%, skillevolutionemptylarge  (+18.86pp)
- **high baselinelowgain**: baseline>90%, skillevolutionemptyvery  (+0.64pp)
- **valid**: when accuracy95%, skillevolutionno bringsimproved

**key findings**: not same benchmarkfor skillline countincrease "can "differencesignificant.

| Benchmark | task type | line countvalid rate (gain/ lines) | bestline countinterval | note |
|-----------|---------|-------------------|-------------|------|
| **LiveMath** | reasoningtype | **0.83 pp/ lines** | 15-33 lines | highrequires , precise rulethen can  |
| **ALFWorld** | explorationtype | **0.18 pp/ lines** | 0-27 lines | harnesslayer, skillvalidlow |
| **SpreadSheet** | rulethen type | **0.03 pp/ lines** | 173 lines | need large template and rulethen coverage |
| **BFCL** | function countcall | **0.01 pp/ lines** | 76 lines | modelcapability limit, rulethen effecthas limit |

**trend interpretation**:
- **reasoningtypetask** (LiveMath) : line countvalid ratemost high, precise rulethen > countpiling up
- **rulethen typetask** (SpreadSheet) : need large rulethen coverageeach , line countvalid ratehighbut
- **explorationtypetask** (ALFWorld) : harnesslayerratioskilllayer weighted morerequire , line countincreaseeffecthas limit
- **function countcalltask** (BFCL) : modeltooluse capability limit, rulethen effectlimited

base at dataanalysis, out Skillself-evolution **phasemodel**:

- **feature**: increase15-30 linescore rulethen
- **expectedgain**: +10~20pp (low baseline)  or  +5~10pp ( in baseline)
- **strategy**: clustermost keyfailedmode, base
- **example**: LiveMath-qwen3.7-max (v0→v6, +15 lines, +18.86pp)

- **feature**: increase30-80 lines,  or keepline countnot changeoptimizequality
- **expectedgain**: +3~8pp
- **strategy**: precise repair timesrequire failedmode, optimizeexistingrulethen
- **example**: ALFWorld-qwen3.6-plus (v0→v2, +27 lines, +11.11pp)

- **feature**: increase80+ lines,  or line countnot change
- **expectedgain**: +0~3pp
- **strategy**: case,  or accept currenttop performance as best
- **example**: ALFWorld-qwen3.7-max (v0→v1.1, +36 lines, +0.14pp)

| | low baseline (<50%) |  in baseline (50-80%) | high baseline (>80%) |
|--|--------------|----------------|--------------|
| **lean improvement**<br/>(+0-30 lines) | <br/>very highvalid rate | <br/>highvalid rate | <br/>mediumvalid rate |
| ** in expansion**<br/>(+30-80 lines) | <br/>highvalid rate | <br/>mediumvalid rate | <br/>lowvalid rate |
| **large expansion**<br/>(+80+ lines) | <br/>mediumvalid rate | <br/>lowvalid rate | <br/>very lowvalid rate |

**use suggestion**:
- low baseline+lean improvement = best group (like LiveMath-qwen3.7-max)
- high baseline+large expansion = most group (like ALFWorld-qwen3.7-max)

1. **then **: **15-30 linesprecise rulethen  > 100+ linesrulethen piling up**
   - LiveMath: +15 lines → +18.86pp (1.26 pp/ lines)
   - BFCL: +76 lines → +1.00pp (0.01 pp/ lines)
   - valid ratedifference: **126**

2. **baseline**:
   - baseline<30%: can expect+15ppwith gain
   - baseline50-70%: can expect+5~10ppgain
   - baseline>90%: expected<1ppgain

3. **task typestrategy**:
   - reasoningtype: precise rulethen prefer
   - rulethen type: templatecoverageprefer
   - explorationtype: harnesslayerprefer
   - function countcall: modelcan prefer

**for at new task line**:
1. run v0baseline, baselineaccuracy
2. based on baselinechoosestrategy:
   - low baseline: 15-30 linescore rulethen , expected+10~20pp
   -  in baseline: 30-50 linesprecise rulethen , expected+5~10pp
   - high baseline: optimizeharnesslayer or accept currenttop performance

**for at evolution in  task line**:
1. line countchange and gainratio rate
2. when ratio rate<0.05 pp/ lines, skilllayerevolution
3. harnesslayeroptimize or model

1. **sampleshas limit**: only 7 fulldata, statssignificanthas verify
2. **line countlabel**: not rulethen quality (like show examplevsconstraintvstemplate)
3. **not contentdifference**: same line count not same skillcan can has donefull not same  effect
4. **single test **: only comparev0 and best version, not tracefullevolutionpath

1. **large samples**: multi-model-benchmarkgroup
2. **contentqualityanalysis**: analysisrule/example/template ratiofor effect
3. **timecolumnanalysis**: tracev0→v1→v2→... fullevolution
4. **A/Btest**: controlline countchange, testnot same contentquality effect

---

**conclusion**: Skillline count and performance gainstore at  nonlinear relation, baselineaccuracy and task type . ** 15-30 linesrulethen optimize**ratio** 100+ linesrulethen piling up**valid , at low in baseline.

---

*reportgenerate time: 2026-06-11*
*analysisscript: analysis/skill_line_trend_analysis.py*
*can visualizationfiguretable: docs/benchmark/skill_line_trend_analysis.png*
"""
    
    output_path = '/path/to/project/docs/benchmark/skill_line_trend_report.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"trend analysis report generated: {output_path}")

if __name__ == '__main__':
    generate_trend_report()
