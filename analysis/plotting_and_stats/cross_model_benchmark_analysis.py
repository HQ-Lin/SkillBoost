#!/usr/bin/env python3
import os
import re
import json
import glob
from pathlib import Path

def parse_benchmark_report(file_path):
    """parsebenchmarkreport, extractkeyperformancedata"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
                        
    filename = os.path.basename(file_path)
    match = re.match(r'(.+?)_(.+?)\.md', filename)
    if not match:
        return None
    
    model_name = match.group(1).replace('-', '.').replace('opus', 'opus')
    benchmark_name = match.group(2).replace('.md', '')
    
                 
    versions_data = {}
    
                       
                                                       
                     
    
    lines = content.split('\n')
    in_table = False
    
    for line in lines:
                
        if '| version |' in line or '| version |' in line.replace('*', ''):
            in_table = True
            continue
        
                
        if in_table and not line.strip().startswith('|'):
            in_table = False
            continue
        
        if in_table and '|' in line:
                   
            cells = [cell.strip() for cell in line.split('|')]
            
                         
            version_cell = None
            accuracy_cell = None
            
            for i, cell in enumerate(cells):
                         
                clean_cell = re.sub(r'\*+', '', cell).strip()
                
                          
                if re.match(r'^(v?\d+\.?\d*|zero_baseline|no.?skill|no skill|baseline)$', clean_cell, re.IGNORECASE):
                    version_cell = clean_cell.lower()
                
                           
                if '%' in cell:
                             
                    pct_match = re.search(r'(\d+\.?\d*)\s*%', cell)
                    if pct_match:
                        accuracy_val = float(pct_match.group(1))
                                    
                        if 0 <= accuracy_val <= 100:
                            accuracy_cell = accuracy_val
            
            if version_cell and accuracy_cell is not None:
                        
                if 'zero' in version_cell or 'no' in version_cell or 'no ' in version_cell or version_cell == 'baseline':
                    version_cell = 'zero_baseline'
                elif not version_cell.startswith('v') and version_cell != 'zero_baseline':
                    version_cell = f'v{version_cell}'
                
                versions_data[version_cell] = accuracy_cell
    
                         
    if not versions_data:
                          
        pattern = re.compile(r'\|\s*\*?\*?(v?\d+\.?\d*|zero_baseline|no.?skill|no skill|baseline)\*?\*?\s*\|.*?(\d+\.?\d*)\s*%', re.IGNORECASE)
        
        for match in pattern.finditer(content):
            version = match.group(1).lower()
            accuracy = float(match.group(2))
            
            if 0 <= accuracy <= 100:
                if 'zero' in version or 'no' in version or 'no ' in version or version == 'baseline':
                    version = 'zero_baseline'
                elif not version.startswith('v') and version != 'zero_baseline':
                    version = f'v{version}'
                
                versions_data[version] = accuracy
    
               
    v0_accuracy = versions_data.get('v0', None)
    
                                 
    best_version = None
    best_accuracy = 0
    for version, accuracy in versions_data.items():
        if version != 'zero_baseline' and accuracy > best_accuracy:
            best_accuracy = accuracy
            best_version = version
    
                        
    if v0_accuracy is None:
                         
        for version in versions_data:
            if 'base' in version and version != 'zero_baseline':
                v0_accuracy = versions_data[version]
                break
    
    return {
        'model': model_name,
        'benchmark': benchmark_name,
        'v0_accuracy': v0_accuracy,
        'best_version': best_version,
        'best_accuracy': best_accuracy,
        'all_versions': versions_data,
        'performance_gain': best_accuracy - v0_accuracy if (v0_accuracy is not None and best_accuracy > 0) else None
    }

def count_skill_lines(skill_path):
    """computeskillfile line count"""
    if not os.path.exists(skill_path):
        return None
    
    with open(skill_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return len(lines)

def find_skill_files(model_benchmark_dir):
    """finddirectory in  skillfile"""
    skill_files = {}
    
              
    for item in os.listdir(model_benchmark_dir):
        item_path = os.path.join(model_benchmark_dir, item)
        if os.path.isdir(item_path):
            skill_md = os.path.join(item_path, 'SKILL.md')
            if os.path.exists(skill_md):
                skill_files[item] = skill_md
    
    return skill_files

def analyze_all_benchmarks():
    """analysisallbenchmarkreport"""
    benchmark_dir = '/path/to/project/docs/benchmark'
    report_files = glob.glob(os.path.join(benchmark_dir, '*.md'))
    
    results = []
    
    for report_file in report_files:
        try:
            data = parse_benchmark_report(report_file)
            if data:
                results.append(data)
        except Exception as e:
            print(f"parse {report_file}  error at: {e}")
    
    return results

def generate_summary_report(results):
    """generate summaryreport"""
    summary = {
        'benchmarks': {},
        'models': {},
        'overall_insights': []
    }
    
                       
    for result in results:
        benchmark = result['benchmark']
        model = result['model']
        
        if benchmark not in summary['benchmarks']:
            summary['benchmarks'][benchmark] = {}
        
        summary['benchmarks'][benchmark][model] = result
        
        if model not in summary['models']:
            summary['models'][model] = {}
        
        summary['models'][model][benchmark] = result
    
          
    for benchmark, models_data in summary['benchmarks'].items():
        benchmark_insights = []
        for model, data in models_data.items():
            if data['performance_gain'] is not None:
                benchmark_insights.append(f"{model}: v0={data['v0_accuracy']:.2f}% → best={data['best_accuracy']:.2f}% ({data['best_version']}) gain={data['performance_gain']:+.2f}pp")
        
        if benchmark_insights:
            summary['overall_insights'].append(f"\n{benchmark}:")
            summary['overall_insights'].extend(benchmark_insights)
    
    return summary

def main():
    print("start analyzing allbenchmarkreport...")
    
            
    results = analyze_all_benchmarks()
    
    if not results:
        print("no valid benchmarkreport")
        return
    
    print(f"parsed successfully {len(results)}  reports")
    
            
    summary = generate_summary_report(results)
    
          
    print("\n=== cross-model cross-Benchmarkperformance analysis summary ===\n")
    
    for benchmark, models_data in sorted(summary['benchmarks'].items()):
        print(f"\n {benchmark}")
        print("-" * 50)
        for model, data in sorted(models_data.items()):
            v0_acc = data['v0_accuracy']
            best_acc = data['best_accuracy']
            best_ver = data['best_version']
            gain = data['performance_gain']
            
            v0_str = f"{v0_acc:.2f}%" if v0_acc is not None else "N/A"
            gain_str = f"{gain:+.2f}pp" if gain is not None else "N/A"
            
            print(f"  {model}:")
            print(f"    v0accuracy: {v0_str}")
            print(f"    best version: {best_ver} ({best_acc:.2f}%)")
            print(f"    performance gain: {gain_str}")
    
            
    output_path = '/path/to/project/docs/benchmark/cross_model_benchmark_analysis.md'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# cross-model cross-Benchmarkperformance analysis summary\n\n")
        f.write(f"> analysistime: 2026-06-11\n")
        f.write(f"> analysisscope: ALFWorld, SpreadSheet, LiveMath, BFCL four Benchmark\n")
        f.write(f">  and model: qwen3.7-max, qwen3.6-plus, kimi-k2.6, claude-opus-4-6, deepseek-v4-pro\n\n")
        
        f.write("## 1. total\n\n")
        
                     
        max_gain = -float('inf')
        min_gain = float('inf')
        max_gain_info = None
        min_gain_info = None
        
        for result in results:
            if result['performance_gain'] is not None:
                if result['performance_gain'] > max_gain:
                    max_gain = result['performance_gain']
                    max_gain_info = result
                if result['performance_gain'] < min_gain:
                    min_gain = result['performance_gain']
                    min_gain_info = result
        
        if max_gain_info:
            f.write(f"###  max performance gain\n")
            f.write(f"- **{max_gain_info['benchmark']} - {max_gain_info['model']}**: ")
            f.write(f"v0={max_gain_info['v0_accuracy']:.2f}% → best={max_gain_info['best_accuracy']:.2f}% ")
            f.write(f"({max_gain_info['best_version']}) gain=**+{max_gain:.2f}pp**\n\n")
        
        if min_gain_info:
            f.write(f"###  min performance gain\n")
            f.write(f"- **{min_gain_info['benchmark']} - {min_gain_info['model']}**: ")
            f.write(f"v0={min_gain_info['v0_accuracy']:.2f}% → best={min_gain_info['best_accuracy']:.2f}% ")
            f.write(f"({min_gain_info['best_version']}) gain=**{min_gain:+.2f}pp**\n\n")
        
        f.write("## 2. Benchmarkdetailed analysis\n\n")
        
        for benchmark, models_data in sorted(summary['benchmarks'].items()):
            f.write(f"### {benchmark}\n\n")
            f.write("| model | v0accuracy | best version | best accuracy | performance gain |\n")
            f.write("|------|----------|----------|------------|----------|\n")
            
            for model, data in sorted(models_data.items()):
                v0_acc = data['v0_accuracy']
                best_acc = data['best_accuracy']
                best_ver = data['best_version']
                gain = data['performance_gain']
                
                v0_str = f"{v0_acc:.2f}%" if v0_acc is not None else "N/A"
                gain_str = f"{gain:+.2f}pp" if gain is not None else "N/A"
                
                f.write(f"| {model} | {v0_str} | {best_ver} | {best_acc:.2f}% | {gain_str} |\n")
            
            f.write("\n")
        
        f.write("## 3. key insight\n\n")
        
                                 
        f.write("### 3.1 Skillself-evolutioneffectdistribution\n\n")
        
        high_gain = [r for r in results if r['performance_gain'] is not None and r['performance_gain'] > 5]
        medium_gain = [r for r in results if r['performance_gain'] is not None and 0 < r['performance_gain'] <= 5]
        low_gain = [r for r in results if r['performance_gain'] is not None and r['performance_gain'] <= 0]
        
        f.write(f"- **highgain (>5pp)**: {len(high_gain)}  example\n")
        for r in high_gain:
            f.write(f"  - {r['benchmark']} - {r['model']}: +{r['performance_gain']:.2f}pp\n")
        
        f.write(f"\n- ** in gain (0-5pp)**: {len(medium_gain)}  example\n")
        for r in medium_gain:
            f.write(f"  - {r['benchmark']} - {r['model']}: +{r['performance_gain']:.2f}pp\n")
        
        f.write(f"\n- **lowgain/regression (≤0pp)**: {len(low_gain)}  example\n")
        for r in low_gain:
            f.write(f"  - {r['benchmark']} - {r['model']}: {r['performance_gain']:+.2f}pp\n")
        
        f.write("\n### 3.2 modelcan  and Skillevolution\n\n")
        f.write("- **baselinemodel** (like qwen3.7-maxat ALFWorld) : Skillevolutionempty, baseline\n")
        f.write("- **mediumbaselinemodel** (like qwen3.7-maxat SpreadSheet) : Skillevolutioncan bringssignificant improvement (+5pplevel) \n")
        f.write("- **baselinemodel** (like qwen3.7-maxat LiveMath) : Skillevolutionemptylarge gap, but limited by modelreasoningcapability limit\n")
        
        f.write("\n### 3.3 Benchmarkfeature\n\n")
        f.write("- **ALFWorld**: explorationtypetask, harnesslayer enhancement ratioskilllayer weighted morerequire \n")
        f.write("- **SpreadSheet**: rulethen typetask, skillprovides methodological guidance valuevaluelarge \n")
        f.write("- **LiveMath**: reasoningtypetask, need  erroridentify and outputformatcontrol\n")
        f.write("- **BFCL**: function countcalltask, limitedat model tooluse capability boundary\n")
    
    print(f"\n summary report saved to: {output_path}")
    
                       
    json_path = '/path/to/project/docs/benchmark/cross_model_benchmark_analysis.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"JSONdata saved to: {json_path}")

if __name__ == '__main__':
    main()
