#!/usr/bin/env python3
import json
import random
import subprocess
import sys
from pathlib import Path

random.seed(42)

                                                         
    
                                                         
BASE = Path("evolved/livemath-solver-qwen36plus")
MODEL = "qwen3.6-plus"
DATA = Path("data/livemath/train.jsonl")
EVAL_SCRIPT = Path("benchmarks/evaluators/test_livemath.py")
MAX_CONCURRENT = 50
SAMPLE_RATIO = 0.3       

print("=" * 70)
print("LiveMath Best-of-N v2 ablation experiment (30% dataquick validation) ")
print("=" * 70)
print()

                   
v1_reports = list(BASE.glob("train_run_*/evals/report_train_*.json"))
v1_reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
v1_report_path = v1_reports[0]

print(f"v1 baseline: {v1_report_path}")

v1_report = json.load(open(v1_report_path))
v1_accuracy = v1_report['accuracy']
fail_ids = v1_report.get('wrong_ids', [])

print(f"v1 accuracy: {v1_accuracy}%")
print(f"v1 failedset: {len(fail_ids)}  questions")
print()

                     
phase_a_ids = random.sample(fail_ids, max(1, int(len(fail_ids) * SAMPLE_RATIO)))
print(f"Phase A sample count (30% failure set): {len(phase_a_ids)}")

                      
all_data = [json.loads(line) for line in open(DATA)]
all_ids = [item['task_id'] for item in all_data]
phase_b_ids = random.sample(all_ids, max(1, int(len(all_ids) * SAMPLE_RATIO)))
print(f"Phase B sample count (30% full set): {len(phase_b_ids)}")
print()

                                                         
               
                                                         
print("=" * 70)
print("Phase A: directed coarse screening (30% failure set)")
print("=" * 70)
print()

candidates = ['c1', 'c2', 'c3', 'c4']
phase_a_scores = {}

for cand in candidates:
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"evaluate candidate: {cand}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    cand_dir = BASE / f"candidates_v2/{cand}"
    output_base = BASE / f"_bestofn_v2_quick/{cand}_phase_a"
    
    cmd = [
        sys.executable, str(EVAL_SCRIPT),
        "--data", str(DATA),
        "--skill", str(cand_dir),
        "--max-concurrent", str(MAX_CONCURRENT),
        "--output-base", str(output_base),
        "--model", MODEL,
        "--filter-ids"
    ] + phase_a_ids
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f" {cand} evaluation failed")
        phase_a_scores[cand] = 0.0
        continue
    
           
    reports = list(output_base.glob("train_run_*/evals/report_train_*.json"))
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    if reports:
        report = json.load(open(reports[0]))
        acc = report['accuracy']
        phase_a_scores[cand] = acc
        print(f" {cand} Phase A accuracy: {acc}%")
    else:
        print(f"report file not found")
        phase_a_scores[cand] = 0.0
    
    print()

            
print("=" * 70)
print("Phase A resultsranking:")
print("=" * 70)
sorted_phase_a = sorted(phase_a_scores.items(), key=lambda x: x[1], reverse=True)
for cand, acc in sorted_phase_a:
    print(f"  {cand}: {acc}%")

         
top2 = [cand for cand, _ in sorted_phase_a[:2]]
print(f"\n Top-2 entering  Phase B: {', '.join(top2)}")
print()

                                                         
                         
                                                         
print("=" * 70)
print("Phase B: full-set selection (30% full setsamples) ")
print("=" * 70)
print()

phase_b_scores = {}

for cand in top2:
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"evaluate candidate: {cand} (Phase B)")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    cand_dir = BASE / f"candidates_v2/{cand}"
    output_base = BASE / f"_bestofn_v2_quick/{cand}_phase_b"
    
    cmd = [
        sys.executable, str(EVAL_SCRIPT),
        "--data", str(DATA),
        "--skill", str(cand_dir),
        "--max-concurrent", str(MAX_CONCURRENT),
        "--output-base", str(output_base),
        "--model", MODEL,
        "--filter-ids"
    ] + phase_b_ids
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f" {cand} Phase B evaluation failed")
        phase_b_scores[cand] = 0.0
        continue
    
           
    reports = list(output_base.glob("train_run_*/evals/report_train_*.json"))
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    if reports:
        report = json.load(open(reports[0]))
        acc = report['accuracy']
        phase_b_scores[cand] = acc
        print(f" {cand} Phase B accuracy: {acc}%")
    else:
        print(f"report file not found")
        phase_b_scores[cand] = 0.0
    
    print()

                                                         
      
                                                         
print("=" * 70)
print("Best-of-N v2 ablation experimentresults summary (30% data)")
print("=" * 70)
print()
print(f"Baseline (v1): {v1_accuracy}% (full set 35 questions)")
print()
print("Phase A (30% failure set):")
for cand in candidates:
    print(f"  {cand}: {phase_a_scores[cand]}%")
print()
print("Phase B (30% full set):")
for cand in top2:
    print(f"  {cand}: {phase_b_scores[cand]}%")
print()

        
winner = max(phase_b_scores.items(), key=lambda x: x[1])
print(f"Winner: {winner[0]} ({winner[1]}%)")
print()

      
result = {
    "experiment": "LiveMath Best-of-N v2 Quick Ablation (30%)",
    "baseline": {
        "version": "v1",
        "accuracy": v1_accuracy,
        "total": 35
    },
    "phase_a": {
        "sample_size": len(phase_a_ids),
        "sample_ratio": SAMPLE_RATIO,
        "scores": phase_a_scores
    },
    "phase_b": {
        "sample_size": len(phase_b_ids),
        "sample_ratio": SAMPLE_RATIO,
        "scores": phase_b_scores
    },
    "winner": {
        "candidate": winner[0],
        "accuracy": winner[1]
    }
}

output_file = BASE / "_bestofn_v2_quick/ablation_result.json"
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"resultssaved: {output_file}")
print("=" * 70)
