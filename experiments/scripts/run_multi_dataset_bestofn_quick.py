#!/usr/bin/env python3
import json
import random
import subprocess
import sys
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

random.seed(42)

                                                         
    
                                                         
DATASETS = {
    'ALFWorld': {
        'base': 'evolved/alfworld-solver-kimi-k2.6',
        'eval_script': 'benchmarks/evaluators/test_alfworld.py',
        'data': 'data/alfworld/train.jsonl',
        'model': 'kimi-k2.6',
        'skill_arg': '--skill',
        'metric_key': 'pass_rate',
        'fail_key': 'fail_ids',
    },
    'DocVQA': {
        'base': 'evolved/docvqa-solver-qwen37plus',
        'eval_script': 'benchmarks/evaluators/test_docvqa.py',
        'data': 'data/docvqa/train.jsonl',
        'model': 'qwen3.7-plus',
        'skill_arg': '--skill',
        'metric_key': 'accuracy',
        'fail_key': 'wrong_ids',
    },
    'OfficeQA': {
        'base': 'evolved/officeqa-solver',
        'eval_script': 'benchmarks/evaluators/test_officeqa.py',
        'data': 'data/officeqa/train.jsonl',
        'model': 'qwen3.6-plus',
        'skill_arg': '--skill',
        'metric_key': 'accuracy',
        'fail_key': 'fail_ids',                          
    },
}

SAMPLE_RATIO = 0.3       
MAX_CONCURRENT = 30            

def get_latest_report(base_path):
    """take most new  evaluation report"""
    import glob
    reports = glob.glob(f'{base_path}/train_run_*/evals/report_train_*.json')
    if not reports:
        reports = glob.glob(f'{base_path}/**/report_train_*.json', recursive=True)
    if reports:
        reports.sort(reverse=True)
        return reports[0]
    return None

def create_candidate_skill(dataset_name, base_path, cand_id, version_suffix):
    """ as not same datasetcreatecandidate SKILL.md"""
    
    if dataset_name == 'ALFWorld':
        candidates = {
            'c1': {
                'name': 'enhancestatusinferred',
                'changes': 'reinforcefor status reasoning, increaseresults semantics'
            },
            'c2': {
                'name': 'simpleempty',
                'changes': 'not must require  trying, clustercorecolumn'
            },
            'c3': {
                'name': 'taskoptimize',
                'changes': 'task as  sub tasksteps'
            },
            'c4': {
                'name': 'errorstrategy',
                'changes': 'enhancefailedafter  retry and '
            }
        }
    elif dataset_name == 'DocVQA':
        candidates = {
            'c1': {
                'name': 'reinforceOCR',
                'changes': 'enhancefor docsstructure and OCRresults '
            },
            'c2': {
                'name': 'answerformatspec',
                'changes': 'strictspecansweroutputformat, formaterror'
            },
            'c3': {
                'name': 'multi-',
                'changes': 'good figure and textinfo'
            },
            'c4': {
                'name': 'filter',
                'changes': 'increaseanswer and filter'
            }
        }
    elif dataset_name == 'OfficeQA':
        candidates = {
            'c1': {
                'name': 'tool callsoptimize',
                'changes': 'optimizesub tabletool callstrategy'
            },
            'c2': {
                'name': ' countvaluecomputeenhance',
                'changes': 'enhance countvaluecompute and can '
            },
            'c3': {
                'name': 'datalocateoptimize',
                'changes': 'datafind and locatestrategy'
            },
            'c4': {
                'name': 'errorenhance',
                'changes': 'enhanceexceptioncase and retry'
            }
        }
    
    cand = candidates[cand_id]
    
                   
    skill_path = os.path.join(base_path, 'SKILL.md')
    if os.path.exists(skill_path):
        with open(skill_path, 'r') as f:
            content = f.read()
    else:
        content = f"# {dataset_name} Solver\n\nBase skill for {dataset_name} tasks.\n"
    
            
    modified_content = content + f"\n\n## v2 {cand['name']} ({version_suffix})\n\n{cand['changes']}\n"
    
    return modified_content

def run_eval(dataset_name, config, cand_id, cand_content, fail_ids, output_base):
    """run single  candidate evaluation"""
    base = config['base']
    cand_dir = os.path.join(base, f'candidates_v2_{cand_id}')
    os.makedirs(cand_dir, exist_ok=True)
    
    skill_path = os.path.join(cand_dir, 'SKILL.md')
    with open(skill_path, 'w') as f:
        f.write(cand_content)
    
    cmd = [
        sys.executable, config['eval_script'],
        '--data', config['data'],
        config['skill_arg'], cand_dir,
        '--max-concurrent', str(MAX_CONCURRENT),
        '--output-base', output_base,
        '--model', config['model'],
        '--filter-ids'
    ] + fail_ids
    
    print(f"  start evaluation {dataset_name}/{cand_id}...")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=600          
        )
        
        elapsed = time.time() - start_time
        
              
        import glob
        reports = glob.glob(f'{output_base}/**/report_*.json', recursive=True)
        if reports:
            reports.sort(reverse=True)
            report = json.load(open(reports[0]))
            acc = report.get(config['metric_key'], 0)
            if isinstance(acc, str):
                acc = float(acc.replace('%', ''))
            return {
                'candidate': cand_id,
                'accuracy': acc,
                'elapsed': elapsed,
                'success': True
            }
        else:
            return {
                'candidate': cand_id,
                'accuracy': 0,
                'elapsed': elapsed,
                'success': False,
                'error': 'No report generated'
            }
    except subprocess.TimeoutExpired:
        return {
            'candidate': cand_id,
            'accuracy': 0,
            'elapsed': 600,
            'success': False,
            'error': 'Timeout'
        }
    except Exception as e:
        return {
            'candidate': cand_id,
            'accuracy': 0,
            'elapsed': time.time() - start_time,
            'success': False,
            'error': str(e)
        }

def run_dataset_ablation(dataset_name, config):
    """run single  dataset fullablation experiment"""
    print(f"\n{'='*70}")
    print(f"dataset: {dataset_name}")
    print(f"{'='*70}")
    
    base = config['base']
    
            
    baseline_report_path = get_latest_report(base)
    if not baseline_report_path:
        print(f" {dataset_name}: not found:baselinereport")
        return {'dataset': dataset_name, 'status': 'error', 'error': 'No baseline report'}
    
    baseline_report = json.load(open(baseline_report_path))
    baseline_acc = baseline_report.get(config['metric_key'], 0)
    if isinstance(baseline_acc, str):
        baseline_acc = float(baseline_acc.replace('%', ''))
    fail_ids = baseline_report.get(config['fail_key'], [])
    total = baseline_report.get('total', baseline_report.get('n_cases', 0))
    
    if not fail_ids:
        print(f"  {dataset_name}: no has failedsamples, skipped")
        return {'dataset': dataset_name, 'status': 'skipped', 'reason': 'No fail_ids'}
    
    print(f"baselineaccuracy: {baseline_acc}% (total={total}, fail={len(fail_ids)})")
    
                
    sample_size = max(1, int(len(fail_ids) * SAMPLE_RATIO))
    phase_a_ids = random.sample(fail_ids, sample_size)
    print(f"Phase A sample count (30%) : {len(phase_a_ids)}")
    
                   
    candidates = ['c1', 'c2', 'c3', 'c4']
    candidate_results = {}
    
                       
    print(f"\n--- Phase A: directed coarse screening ---")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for cand_id in candidates:
            cand_content = create_candidate_skill(dataset_name, base, cand_id, 'quick_ablation')
            output_base = os.path.join(base, f'_bestofn_v2_quick/{cand_id}_phase_a')
            future = executor.submit(
                run_eval, 
                dataset_name, config, cand_id, cand_content, phase_a_ids, output_base
            )
            futures[future] = cand_id
        
        for future in as_completed(futures):
            result = future.result()
            candidate_results[result['candidate']] = result
            status = ''if result['success'] else ''
            print(f"  {status} {result['candidate']}: {result['accuracy']}% ({result['elapsed']:.1f}s)")
    
                
    sorted_candidates = sorted(
        candidate_results.items(), 
        key=lambda x: x[1]['accuracy'], 
        reverse=True
    )
    top2 = [c for c, _ in sorted_candidates[:2]]
    
    print(f"\n Phase A Top-2: {', '.join(top2)}")
    
                                 
    print(f"\n--- Phase B: full-set selection (30% full set) ---")
    
            
    data_path = config['data']
    if os.path.exists(data_path):
        all_data = [json.loads(line) for line in open(data_path)]
        all_ids = [item['task_id'] for item in all_data]
        phase_b_ids = random.sample(all_ids, max(1, int(len(all_ids) * SAMPLE_RATIO)))
        print(f"Phase B sample count (30% full set): {len(phase_b_ids)}")
    else:
        print(f"datafile not found: {data_path}, use  Phase A samples")
        phase_b_ids = phase_a_ids
    
    phase_b_results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        for cand_id in top2:
            cand_dir = os.path.join(base, f'candidates_v2_{cand_id}')
            with open(os.path.join(cand_dir, 'SKILL.md'), 'r') as f:
                cand_content = f.read()
            output_base = os.path.join(base, f'_bestofn_v2_quick/{cand_id}_phase_b')
            future = executor.submit(
                run_eval,
                dataset_name, config, cand_id, cand_content, phase_b_ids, output_base
            )
            futures[future] = cand_id
        
        for future in as_completed(futures):
            result = future.result()
            phase_b_results[result['candidate']] = result
            status = ''if result['success'] else ''
            print(f"  {status} {result['candidate']}: {result['accuracy']}% ({result['elapsed']:.1f}s)")
    
               
    if phase_b_results:
        winner = max(phase_b_results.items(), key=lambda x: x[1]['accuracy'])
        winner_name = winner[0]
        winner_acc = winner[1]['accuracy']
    else:
        winner_name = 'None'
        winner_acc = 0
    
        
    print(f"\n{'='*70}")
    print(f" {dataset_name} ablation experimentresults")
    print(f"{'='*70}")
    print(f"Baseline: {baseline_acc}%")
    print(f"Phase A results:")
    for cand, res in sorted_candidates:
        print(f"  {cand}: {res['accuracy']}%")
    print(f"Phase B results:")
    for cand in top2:
        if cand in phase_b_results:
            print(f"  {cand}: {phase_b_results[cand]['accuracy']}%")
    print(f"Winner: {winner_name} ({winner_acc}%)")
    
    return {
        'dataset': dataset_name,
        'baseline': {
            'accuracy': baseline_acc,
            'total': total,
            'fail_count': len(fail_ids)
        },
        'phase_a': {c: r['accuracy'] for c, r in sorted_candidates},
        'phase_b': {c: phase_b_results[c]['accuracy'] for c in top2 if c in phase_b_results},
        'winner': winner_name,
        'winner_accuracy': winner_acc,
        'delta': winner_acc - baseline_acc
    }

def main():
    print("=" * 70)
    print("multi-dataset Best-of-N v2 quick ablation experiment (30% data)")
    print("=" * 70)
    print(f"sampling ratio: {SAMPLE_RATIO*100}%")
    print(f"concurrency count: {MAX_CONCURRENT}")
    print()
    
    results = {}
    
                       
    for dataset_name, config in DATASETS.items():
        result = run_dataset_ablation(dataset_name, config)
        results[dataset_name] = result
        print()
    
          
    print("\n" + "=" * 70)
    print("full datasetablation experiment summary")
    print("=" * 70)
    print()
    print(f"{'dataset':<15} {'baseline':>8} {'Winner':>8} {'Δ':>8} {'status':>10}")
    print("-" * 55)
    
    for name, result in results.items():
        if result.get('status') == 'error':
            print(f"{name:<15} {'-':>8} {'-':>8} {'-':>8} {'ERROR':>10}")
        elif result.get('status') == 'skipped':
            print(f"{name:<15} {'-':>8} {'-':>8} {'-':>8} {'SKIPPED':>10}")
        else:
            baseline = result['baseline']['accuracy']
            winner_acc = result['winner_accuracy']
            delta = result['delta']
            status = 'improved 'if delta > 0 else (''if delta == 0 else 'regression')
            print(f"{name:<15} {baseline:>7.1f}% {winner_acc:>7.1f}% {delta:>+7.1f} {status:>10}")
    
            
    output_file = 'bestofn_v2_quick_ablation_summary.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n detailed resultssaved: {output_file}")
    print("=" * 70)

if __name__ == '__main__':
    main()
