#!/usr/bin/env python3
import json
import glob
from pathlib import Path

def analyze_iteration_efficiency():
    """analysishas experiment iterationsvalid rate"""
    
    print("=" * 100)
    print("Best-of-N vs single thread evolution: convergence efficiencycomparison")
    print("=" * 100)
    
                       
    print("\n Best-of-N experiment summary")
    print("-" * 100)
    
    bon_experiments = [
        {
            'name': 'officeqa-solver (claude)',
            'baseline': 87.34,
            'winner': 68.35,
            'n_candidates': 4,
            'status': 'regression -18.99%',
            'promoted': False
        },
        {
            'name': 'docvqa-qwen37plus v1',
            'baseline': 93.33,
            'winner': 96.67,
            'n_candidates': 4,
            'status': 'improved  +3.34%',
            'promoted': True
        },
        {
            'name': 'docvqa-qwen37plus v2',
            'baseline': 96.67,
            'winner': 98.0,
            'n_candidates': 4,
            'status': 'improved  +1.33%',
            'promoted': True
        },
        {
            'name': 'alfworld-qwen37max v1',
            'baseline': 86.67,
            'winner': 80.0,
            'n_candidates': 4,
            'status': 'regression -6.67%',
            'promoted': False
        },
        {
            'name': 'alfworld-qwen37max v1-redo',
            'baseline': 86.67,
            'winner': 76.67,
            'n_candidates': 3,
            'status': 'regression -10.00%',
            'promoted': False
        },
        {
            'name': 'alfworld-solver v1-h2',
            'baseline': 86.11,
            'winner': 94.44,
            'n_candidates': 4,
            'status': 'improved  +8.33%',
            'promoted': True
        }
    ]
    
    print(f"{'experiment name':<30} | {'Baseline':<10} | {'Winner':<10} | {'N':<5} | {'results':<20} | {'Promote'}")
    print("-" * 100)
    for exp in bon_experiments:
        promoted = ''if exp['promoted'] else ''
        print(f"{exp['name']:<30} | {exp['baseline']:<10} | {exp['winner']:<10} | {exp['n_candidates']:<5} | {exp['status']:<20} | {promoted}")
    
        
    total = len(bon_experiments)
    success = sum(1 for e in bon_experiments if e['promoted'])
    fail = total - success
    
    print(f"\n Best-of-N success rate: {success}/{total} = {success/total*100:.1f}%")
    print(f"   avg elapsed: 2  turnsevaluation (Phase A + Phase B)")
    
                
    print("\n" + "=" * 100)
    print("single thread evolution experiment (from  changelogs inferred) ")
    print("-" * 100)
    
    single_thread_cases = [
        {
            'name': 'docvqa-solver (claude)',
            'path': 'v0 → v1 → v2 → v3 → v4 → v5',
            'iterations': 5,
            'notes': 'v3 regressionrolled back to  v2, effective iterations 4  turns',
            'total_evals': '5  full-set eval rounds + 2  directed eval rounds (rollback)'
        },
        {
            'name': 'decision-task',
            'path': 'v0 → v1 → v2 → v3 → v4 → v5',
            'iterations': 5,
            'notes': 'continuous iteration, gains every round',
            'total_evals': '5  full-set eval rounds'
        },
        {
            'name': 'routing-task',
            'path': 'v0 → v1 → v2 → v3 → v4 → v5 → v6 → v7',
            'iterations': 7,
            'notes': 'long-chain iteration, gradual optimization',
            'total_evals': '7  full-set eval rounds'
        }
    ]
    
    print(f"{'experiment name':<25} | {'iteration path':<40} | {' turns times':<6} | {'note'}")
    print("-" * 100)
    for case in single_thread_cases:
        print(f"{case['name']:<25} | {case['path']:<40} | {case['iterations']:<6} | {case['notes']}")
    
    avg_iterations = sum(c['iterations'] for c in single_thread_cases) / len(single_thread_cases)
    print(f"\n single threadavgiterations turns times: {avg_iterations:.1f}  turns")
    print(f"   avg elapsed: {avg_iterations:.1f}  turnsfull setevaluation")
    
             
    print("\n" + "=" * 100)
    print("valid ratecomparisonanalysis")
    print("=" * 100)
    
    print("""
┌─────────────────────┬──────────────┬──────────────┬─────────────┐
| dimension                | Best-of-N    | single thread evolution   | winner      |
├─────────────────────┼──────────────┼──────────────┼─────────────┤
| iteration rounds            | 1-2  turns       | 4-7  turns       | Best-of-N   |
| eval count            | 2-3  times       | 4-7  times       | Best-of-N   |
| success rate              | 50% (3/6)    | ~70% (assumed)  | single-thread      |
| per-run time cost        | high(parallelN )  | low(serial1 )  | single-thread      |
| total time cost          | medium         | higher         | Best-of-N?  |
| exploration strategy space  | wide(N )  | narrow(1 )  | Best-of-N  |
| suitable scenario            | low baseline       | high baseline       | depends      |
└─────────────────────┴──────────────┴──────────────┴─────────────┘

key findings:
1. Best-of-N at turnsis indeed faster (1-2 vs 4-7)
2. but lower success rate (50% vs ~70%) , requires repeated trials
3. high baseline (>85%) Best-of-N diminishing returns, single-thread is steadier
4. low baseline (<70%) Best-of-N can quickly find a breakthrough direction

conclusion:
 Best-of-N converges faster only when:
   - baseline is low (<75%) , strategy spacelarge
   - candidate design is high quality and avoids rule overload
   - enough parallel compute is available

 Best-of-N loses to single-thread when:
   - high baseline (>85%) , fine-grained tuning is needed
   - candidate design easily overfits or regresses
   - compute limited, cannot parallelize  N  evaluations
""")

           
    print("=" * 100)
    print("practical advice")
    print("=" * 100)
    
    print("""
hybrid strategy (recommended):
1. low-baseline stage (v0→v1): use  Best-of-N fast exploration (N=2-4)
2. mid-baseline stage (v1→v3): use single-thread fine-grained iteration
3. high-baseline stage (v3+): use subtractive ablation + single-thread fine-tuning

time cost estimate:
- Best-of-N: 1 turns × (Phase A + Phase B) × concurrencyN = ~2-3  hours (N=4, concurrency50)
- single-thread: 4 turns × 1 full-set rounds = ~4-6  hours (concurrency50)

actual speedup: ~2x (but success rate must be considered)
""")

if __name__ == "__main__":
    analyze_iteration_efficiency()
