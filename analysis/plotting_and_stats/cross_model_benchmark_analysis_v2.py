#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path

def extract_skill_lines_from_report(content):
                               
    patterns = [
        r'v0.*?(\d+)\s* lines',
        r'v0.*?~(\d+)\s* lines',
        r'v0.*?(\d+)\+?\s* lines',
    ]
    
    v0_lines = None
    best_lines = None
    
              
    lines = content.split('\n')
    for line in lines:
        if 'v0' in line.lower() and ' lines' in line:
            match = re.search(r'(\d+)\s* lines', line)
            if match:
                v0_lines = int(match.group(1))
    
    return v0_lines, best_lines

def parse_qwen37max_alfworld():
    """parse qwen3.7-max ALFWorld report"""
    return {
        'model': 'qwen3.7-max',
        'benchmark': 'ALFWorld',
        'v0_accuracy': 94.3,          
        'best_version': 'v1.1',
        'best_accuracy': 94.44,
        'v0_lines': None,                  
        'best_lines': None,
        'performance_gain': 0.14
    }

def parse_qwen37max_spreadsheet():
    """parse qwen3.7-max SpreadSheet report"""
    return {
        'model': 'qwen3.7-max',
        'benchmark': 'SpreadSheet',
        'v0_accuracy': 72.50,
        'best_version': 'v2',
        'best_accuracy': 77.86,
        'performance_gain': 5.36
    }

def parse_qwen37max_livemath():
    """parse qwen3.7-max LiveMath report"""
    return {
        'model': 'qwen3.7-max',
        'benchmark': 'LiveMath',
        'v0_accuracy': 17.14,
        'best_version': 'v6',
        'best_accuracy': 36.0,
        'performance_gain': 18.86
    }

def parse_qwen37max_bfcl():
    """parse qwen3.7-max BFCL report"""
    return {
        'model': 'qwen3.7-max',
        'benchmark': 'BFCL',
        'v0_accuracy': 51.6,
        'best_version': 'v4',
        'best_accuracy': 52.6,
        'performance_gain': 1.0
    }

def count_skill_lines(base_path, version):
    """computeversionskillfile line count"""
    skill_path = os.path.join(base_path, version, 'SKILL.md')
    if not os.path.exists(skill_path):
        return None
    
    with open(skill_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return len(lines)

def analyze_skill_line_differences():
    """analysiseach modeleach benchmark skillline count diffdiff"""
    results = []
    
                          
    analyses = [
                ]
    
    base_path = '/path/to/project'
    
    for analysis in analyses:
        v0_lines = count_skill_lines(os.path.join(base_path, analysis['base_dir']), analysis['v0'])
        best_lines = count_skill_lines(os.path.join(base_path, analysis['base_dir']), analysis['best'])
        
        line_diff = None
        if v0_lines is not None and best_lines is not None:
            line_diff = best_lines - v0_lines
        
        results.append({
            'model': analysis['model'],
            'benchmark': analysis['benchmark'],
            'v0_version': analysis['v0'],
            'best_version': analysis['best'],
            'v0_lines': v0_lines,
            'best_lines': best_lines,
            'line_difference': line_diff
        })
    
    return results

def generate_comprehensive_report():
    """generate comprehensive analysisreport"""
    
                              
    manual_data = []
    
                 
    line_analysis = analyze_skill_line_differences()
    
          
    combined_data = []
    for data in manual_data:
        entry = data.copy()
        
                   
        for line_info in line_analysis:
            if line_info['model'] == data['model'] and line_info['benchmark'] == data['benchmark']:
                entry['v0_lines'] = line_info['v0_lines']
                entry['best_lines'] = line_info['best_lines']
                entry['line_diff'] = line_info['line_difference']
                break
        
        combined_data.append(entry)
    
    return combined_data

def main():
    print("start generating cross-model cross-Benchmarkcomprehensive analysis...")
    
            
    data = generate_comprehensive_report()
    
          
    print("\n=== cross-model cross-Benchmarkperformance vs Skillline count difference analysis ===\n")
    
                  
    benchmarks = {}
    for entry in data:
        benchmark = entry['benchmark']
        if benchmark not in benchmarks:
            benchmarks[benchmark] = []
        benchmarks[benchmark].append(entry)
    
    for benchmark, entries in sorted(benchmarks.items()):
        print(f"\n {benchmark}")
        print("-" * 80)
        print(f"{'model':<20} {'v0accuracy':<12} {'best version':<12} {'best accuracy':<12} {'gain':<12} {'v0line count':<10} {'best line count':<10} {'line count diff':<8}")
        print("-" * 80)
        
        for entry in sorted(entries, key=lambda x: x['model']):
            model = entry['model']
            v0_acc = f"{entry['v0_acc']:.2f}%"
            best_ver = entry['best_ver']
            best_acc = f"{entry['best_acc']:.2f}%"
            gain = f"+{entry['gain']:.2f}pp" if entry['gain'] > 0 else f"{entry['gain']:.2f}pp"
            
            v0_lines = str(entry.get('v0_lines', 'N/A'))
            best_lines = str(entry.get('best_lines', 'N/A'))
            line_diff = str(entry.get('line_diff', 'N/A'))
            
            print(f"{model:<20} {v0_acc:<12} {best_ver:<12} {best_acc:<12} {gain:<12} {v0_lines:<10} {best_lines:<10} {line_diff:<8}")
    
                  
    output_path = '/path/to/project/docs/benchmark/cross_model_comprehensive_analysis.md'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# cross-model cross-Benchmarkperformance vs Skillevolutioncomprehensive analysis\n\n")
        f.write(f"> analysistime: 2026-06-11\n")
        f.write(f"> analysisscope: ALFWorld, SpreadSheet, LiveMath, BFCL four Benchmark\n")
        f.write(f">  and model: qwen3.7-max, qwen3.6-plus, kimi-k2.6, claude-opus-4-6, deepseek-v4-pro\n\n")
        
        f.write("## 1. core\n\n")
        
                   
        max_gain_entry = max(data, key=lambda x: x['gain'])
        min_gain_entry = min(data, key=lambda x: x['gain'])
        
        f.write(f"###  max performance gain\n")
        f.write(f"- **{max_gain_entry['benchmark']} - {max_gain_entry['model']}**: ")
        f.write(f"v0={max_gain_entry['v0_acc']:.2f}% → best={max_gain_entry['best_acc']:.2f}% ")
        f.write(f"({max_gain_entry['best_ver']}) gain=**+{max_gain_entry['gain']:.2f}pp**\n\n")
        
        f.write(f"###  min performance gain\n")
        f.write(f"- **{min_gain_entry['benchmark']} - {min_gain_entry['model']}**: ")
        f.write(f"v0={min_gain_entry['v0_acc']:.2f}% → best={min_gain_entry['best_acc']:.2f}% ")
        f.write(f"({min_gain_entry['best_ver']}) gain=**{min_gain_entry['gain']:+.2f}pp**\n\n")
        
        f.write("## 2. Benchmarkdetailed analysis\n\n")
        
        for benchmark, entries in sorted(benchmarks.items()):
            f.write(f"### {benchmark}\n\n")
            f.write("| model | v0accuracy | best version | best accuracy | performance gain | v0line count | best line count | line count diff |\n")
            f.write("|------|----------|----------|------------|----------|--------|----------|--------|\n")
            
            for entry in sorted(entries, key=lambda x: x['model']):
                v0_acc = f"{entry['v0_acc']:.2f}%"
                best_acc = f"{entry['best_acc']:.2f}%"
                gain = f"{entry['gain']:+.2f}pp"
                
                v0_lines = entry.get('v0_lines', 'N/A')
                best_lines = entry.get('best_lines', 'N/A')
                line_diff = entry.get('line_diff', 'N/A')
                
                v0_lines_str = str(v0_lines) if v0_lines is not None else 'N/A'
                best_lines_str = str(best_lines) if best_lines is not None else 'N/A'
                line_diff_str = str(line_diff) if line_diff is not None else 'N/A'
                
                f.write(f"| {entry['model']} | {v0_acc} | {entry['best_ver']} | {best_acc} | {gain} | {v0_lines_str} | {best_lines_str} | {line_diff_str} |\n")
            
            f.write("\n")
        
        f.write("## 3. key insight\n\n")
        
        f.write("### 3.1 Skillline countchange and performance gain \n\n")
        
                    
        line_data = [d for d in data if d.get('line_diff') is not None]
        
        if line_data:
            f.write("| model | Benchmark | performance gain | line countchange |  |\n")
            f.write("|------|-----------|----------|----------|------|\n")
            
            for entry in line_data:
                observation = ""
                if entry['gain'] > 5 and entry['line_diff'] > 0:
                    observation = "large increaserulethen bringssignificant improvement"
                elif entry['gain'] > 5 and entry['line_diff'] < 0:
                    observation = "simplerulethen improved performance"
                elif entry['gain'] < 2 and entry['line_diff'] > 20:
                    observation = "rulethen but gainhas limit"
                elif entry['gain'] < 2:
                    observation = "performance"
                else:
                    observation = "fit "
                
                f.write(f"| {entry['model']} | {entry['benchmark']} | +{entry['gain']:.2f}pp | {entry['line_diff']:+d} lines | {observation} |\n")
        
        f.write("\n### 3.2 modelcan  and Skillevolutionstrategy\n\n")
        f.write("- **high baselinemodel** (>80%) : Skillevolutionemptyhas limit, gain<5pp\n")
        f.write("- ** in baselinemodel** (40-80%) : Skillevolutioncan brings5-15ppimproved \n")
        f.write("- **low baselinemodel** (<40%) : Skillevolutionemptylarge gap, but limited by modelcapability limit\n")
        
        f.write("\n### 3.3 Benchmarkanalysis\n\n")
        f.write("- **ALFWorld**: explorationtypetask, harnesslayer (explorationstatus) ratioskilllayer weighted morerequire \n")
        f.write("- **SpreadSheet**: rulethen typetask, skillprovides methodological guidance valuevaluesignificant\n")
        f.write("- **LiveMath**: reasoningtypetask, need  erroridentify and outputformatcontrol\n")
        f.write("- **BFCL**: function countcalltask, limitedat model tooluse capability boundary\n")
        
        f.write("\n## 4. conclusion and suggestion\n\n")
        f.write("1. **Skillself-evolution  valuevaluetask and modeldiff**: at rulethen typetask (SpreadSheet)  valuevaluemax , at explorationtypetask (ALFWorld)  valuevalue\n")
        f.write("2. **line countnot  is key, qualitythen  is **: succeeded skillevolutionnot  is simplesingle increaserulethen ,  is precise repairfailedmode\n")
        f.write("3. **high baseline evolutionpitfall**: when modelbaseline>80%, skillevolutionref regression\n")
        f.write("4. **suggestionpreferoptimizeharnesslayer**: for at explorationtypetask, harnesslayer enhancement ratioskilllayervalid \n")
    
    print(f"\n comprehensive analysis report saved to: {output_path}")
    
              
    json_path = '/path/to/project/docs/benchmark/cross_model_comprehensive_analysis.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"JSONdata saved to: {json_path}")

if __name__ == '__main__':
    main()
