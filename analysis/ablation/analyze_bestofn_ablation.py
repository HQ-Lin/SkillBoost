#!/usr/bin/env python3
import json
import glob
from pathlib import Path
from typing import Dict, List, Any

def load_reports(base_dir: str = "evolved") -> List[Dict[str, Any]]:
    """loadall selection_report.json"""
    pattern = f"{base_dir}/**/_bestofn*/selection_report.json"
    report_paths = glob.glob(pattern, recursive=True)
    
    reports = []
    for path in report_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                report = json.load(f)
                report['_source_path'] = path
                reports.append(report)
        except Exception as e:
            print(f"loadfailed {path}: {e}")
    
    return reports

def simulate_ablation(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    for single  Best-of-N experimentanalysis
    
    returned not same  N value bestaccuracy (from  Phase B  candidate in take  Top-N)
    """
    baseline_acc = report.get('baseline_full_accuracy')
    phase_b = report.get('phase_b', [])
    
    if not phase_b or baseline_acc is None:
        return None
    
            
    sorted_candidates = sorted(phase_b, key=lambda x: x.get('full_accuracy', 0), reverse=True)
    
                                      
    ablation_results = {
        'N=1 (baseline)': {
            'accuracy': baseline_acc,
            'delta': 0,
            'note': 'baseline'
        }
    }
    
    for n in range(2, len(sorted_candidates) + 1):
        top_n = sorted_candidates[:n]
        best_acc = max(c['full_accuracy'] for c in top_n)
        delta = round(best_acc - baseline_acc, 2)
        
        ablation_results[f'N={n}'] = {
            'accuracy': best_acc,
            'delta': delta,
            'best_candidate': sorted_candidates[0]['candidate'] if n == 1 else top_n[0]['candidate'],
            'note': f'Top-{n}  in best'
        }
    
    return ablation_results

def analyze_marginal_gain(report: Dict[str, Any]) -> Dict[str, Any]:
    """analysismarginal gain"""
    ablation = simulate_ablation(report)
    if not ablation:
        return None
    
    gains = []
    prev_acc = ablation['N=1 (baseline)']['accuracy']
    
    for n in range(2, 5):
        key = f'N={n}'
        if key not in ablation:
            break
        
        curr_acc = ablation[key]['accuracy']
        marginal_gain = round(curr_acc - prev_acc, 2)
        gains.append({
            'from': f'N={n-1}',
            'to': key,
            'marginal_gain': marginal_gain,
            'cumulative_gain': round(curr_acc - ablation['N=1 (baseline)']['accuracy'], 2)
        })
        prev_acc = curr_acc
    
    return {
        'task_line': report.get('task_line', 'unknown'),
        'baseline_acc': ablation['N=1 (baseline)']['accuracy'],
        'n_candidates': report.get('n_candidates'),
        'marginal_gains': gains,
        'source': report['_source_path']
    }

def print_ablation_table(reports: List[Dict[str, Any]]):
    """printablation experiment summarytable"""
    print("\n" + "=" * 120)
    print("Best-of-N ablation experiment summary")
    print("=" * 120)
    
    print(f"\n{'experimentssource':<40} | {'Baseline':<10} | {'N=2':<10} | {'N=3':<10} | {'N=4':<10} | {'best N':<8}")
    print("-" * 120)
    
    for report in reports:
        ablation = simulate_ablation(report)
        if not ablation:
            continue
        
        source = Path(report['_source_path']).parent.name
        baseline = ablation['N=1 (baseline)']['accuracy']
        
        n2 = ablation.get('N=2', {}).get('accuracy', '-')
        n3 = ablation.get('N=3', {}).get('accuracy', '-')
        n4 = ablation.get('N=4', {}).get('accuracy', '-')
        
               
        best_n = 'N=1'
        best_acc = baseline
        for key in ['N=2', 'N=3', 'N=4']:
            if key in ablation and ablation[key]['accuracy'] > best_acc:
                best_acc = ablation[key]['accuracy']
                best_n = key
        
        print(f"{source:<40} | {baseline:<10} | {n2:<10} | {n3:<10} | {n4:<10} | {best_n:<8}")

def print_marginal_analysis(marginal_analyses: List[Dict[str, Any]]):
    """printmarginal gainanalysis"""
    print("\n" + "=" * 120)
    print("Best-of-N marginal gainanalysis")
    print("=" * 120)
    
    for analysis in marginal_analyses:
        if not analysis:
            continue
        
        print(f"\n {analysis['task_line']} (baseline={analysis['baseline_acc']}%, N={analysis['n_candidates']})")
        print(f"  source: {analysis['source']}")
        
        for gain in analysis['marginal_gains']:
            arrow = "↑" if gain['marginal_gain'] > 0 else ("↓" if gain['marginal_gain'] < 0 else "→")
            print(f"  {gain['from']} → {gain['to']}: {arrow} {gain['marginal_gain']:+.2f}% (cumulative : {gain['cumulative_gain']:+.2f}%)")

def print_statistical_summary(marginal_analyses: List[Dict[str, Any]]):
    """printstats summary"""
    print("\n" + "=" * 120)
    print("stats summary")
    print("=" * 120)
    
              
    gains_1_to_2 = []
    gains_2_to_3 = []
    gains_3_to_4 = []
    
    for analysis in marginal_analyses:
        if not analysis:
            continue
        
        for gain in analysis['marginal_gains']:
            if gain['from'] == 'N=1' and gain['to'] == 'N=2':
                gains_1_to_2.append(gain['marginal_gain'])
            elif gain['from'] == 'N=2' and gain['to'] == 'N=3':
                gains_2_to_3.append(gain['marginal_gain'])
            elif gain['from'] == 'N=3' and gain['to'] == 'N=4':
                gains_3_to_4.append(gain['marginal_gain'])
    
    def calc_stats(gains):
        if not gains:
            return "N/A"
        avg = sum(gains) / len(gains)
        positive = sum(1 for g in gains if g > 0)
        negative = sum(1 for g in gains if g < 0)
        zero = sum(1 for g in gains if g == 0)
        return f"avg {avg:+.2f}% | improved  {positive}/{len(gains)} | decrease {negative}/{len(gains)} |  {zero}/{len(gains)}"
    
    print(f"\nN=1 → N=2: {calc_stats(gains_1_to_2)}")
    print(f"N=2 → N=3: {calc_stats(gains_2_to_3)}")
    print(f"N=3 → N=4: {calc_stats(gains_3_to_4)}")
    
        
    print("\n" + "=" * 120)
    print("conclusion")
    print("=" * 120)
    
    if gains_1_to_2:
        avg_gain = sum(gains_1_to_2) / len(gains_1_to_2)
        if avg_gain > 2:
            print("Best-of-N at  N=1→2 phasehas significant improvement (avg +{:.2f}%) , recommend using at least N=2".format(avg_gain))
        elif avg_gain > 0:
            print("Best-of-N at  N=1→2 phasehas slight improvement (avg +{:.2f}%) , gainhas limit".format(avg_gain))
        else:
            print("Best-of-N at  N=1→2 phaseavgdecrease ({:.2f}%) , population search gain is not significant at high baselines".format(avg_gain))
    
    if gains_2_to_3:
        avg_gain = sum(gains_2_to_3) / len(gains_2_to_3)
        print(f"  N=2→3 marginal gain: {avg_gain:+.2f}% ({'diminishing returns' if avg_gain < sum(gains_1_to_2)/len(gains_1_to_2) else 'keeps improving'}) ")
    
    if gains_3_to_4:
        avg_gain = sum(gains_3_to_4) / len(gains_3_to_4)
        print(f"   N=3→4 marginal gain: {avg_gain:+.2f}%")

def main():
    print("load Best-of-N experiment reports...")
    reports = load_reports()
    print(f"found {len(reports)} Best-of-N experiments")

    if not reports:
        print("no Best-of-N experiment data found")
        return

    print_ablation_table(reports)

    marginal_analyses = [analyze_marginal_gain(r) for r in reports]
    print_marginal_analysis(marginal_analyses)

    print_statistical_summary(marginal_analyses)

    print("\n" + "=" * 120)
    print("analysis done")
    print("=" * 120)

if __name__ == "__main__":
    main()
