#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import defaultdict

def load_jsonl(file_path):
    results = []
    if not file_path.exists():
        return results
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results

def analyze_alfworld():
    """analysisALFWorld n_turnsdata"""
    print("=" * 80)
    print("ALFWorld interaction count analysis")
    print("=" * 80)
    
    base_path = Path("evolved/alfworld-solver")
    
                                      
    versions = {
        "v0": base_path / "",
        "v4": base_path / "",
    }
    
    for version_name, results_file in versions.items():
        print(f"\n {version_name}")
        
        if not results_file.exists():
            print(f"     resultsfile not found: {results_file}")
            continue
        
        results = load_jsonl(results_file)
        if not results:
            print(f"     no result data")
            continue
        
        n_turns_list = [r.get("n_turns", 0) for r in results if r.get("n_turns")]
        won_turns = [r.get("n_turns", 0) for r in results if r.get("won") and r.get("n_turns")]
        lost_turns = [r.get("n_turns", 0) for r in results if not r.get("won") and r.get("n_turns")]
        
        print(f"   totalcase count: {len(results)}")
        print(f"   success count: {sum(1 for r in results if r.get('won'))}")
        print(f"   success rate: {sum(1 for r in results if r.get('won'))/len(results)*100:.1f}%")
        
        if n_turns_list:
            print(f"    avg interactions (all): {sum(n_turns_list)/len(n_turns_list):.1f}")
            if won_turns:
                print(f"    avg interactions (succeeded): {sum(won_turns)/len(won_turns):.1f}")
            if lost_turns:
                print(f"    avg interactions (failed): {sum(lost_turns)/len(lost_turns):.1f}")
            print(f"   max interactions: {max(n_turns_list)}")
            print(f"   min interactions: {min(n_turns_list)}")

def analyze_spreadsheet():
    """analysisSpreadSheet n_turnsdata"""
    print("\n" + "=" * 80)
    print("SpreadSheetBench interaction count analysis")
    print("=" * 80)
    
    base_path = Path("evolved/spreadsheetbench-solver")
    
                                       
    versions = {
        "no_skill (Claude)": base_path / "val_run_20260609_103144",
        "v0 (Claude)": base_path / "val_run_20260608_200309",
        "v1 (Claude, best)": base_path / "val_run_20260608_203414",
    }
    
    for version_name, run_dir in versions.items():
        print(f"\n {version_name}")
        
        if not run_dir.exists():
            print(f"     directory not found: {run_dir}")
            continue
        
                     
        results_file = None
        for f in run_dir.glob("results*.jsonl"):
            results_file = f
            break
        
        if not results_file:
            print(f"     not found:resultsfile")
            continue
        
        results = load_jsonl(results_file)
        if not results:
            print(f"     no result data")
            continue
        
        n_turns_list = [r.get("n_turns", 0) for r in results if r.get("n_turns")]
        hard_pass_turns = [r.get("n_turns", 0) for r in results if r.get("hard") == 1 and r.get("n_turns")]
        hard_fail_turns = [r.get("n_turns", 0) for r in results if r.get("hard") == 0 and r.get("n_turns")]
        
        print(f"   totaltask count: {len(results)}")
        print(f"   Hardpass count: {sum(1 for r in results if r.get('hard') == 1)}")
        print(f"   Hardpass rate: {sum(1 for r in results if r.get('hard') == 1)/len(results)*100:.1f}%")
        
        if n_turns_list:
            print(f"    avg interaction turns (all): {sum(n_turns_list)/len(n_turns_list):.1f}")
            if hard_pass_turns:
                print(f"    avg interaction turns (Hardpassed): {sum(hard_pass_turns)/len(hard_pass_turns):.1f}")
            if hard_fail_turns:
                print(f"    avg interaction turns (Hardfailed): {sum(hard_fail_turns)/len(hard_fail_turns):.1f}")
            print(f"   max interaction turns: {max(n_turns_list)}")
            print(f"   min interaction turns: {min(n_turns_list)}")

def analyze_bfcl():
    """analysisBFCL data (call count) """
    print("\n" + "=" * 80)
    print("BFCL function-call count analysis")
    print("=" * 80)
    
    base_path = Path("evolved/bfcl-solver")
    
                                            
    versions = {
        "no_skill (deepseek-v4-pro)": base_path / "evals/run_no_skill_test_deepseek_v4_pro_20260609_205102",
        "v0 (deepseek-v4-pro)": base_path / "evals/run_v0_test_deepseek_v4_pro_20260609_205110",
        "v2 (deepseek-v4-pro, best)": base_path / "evals/run_v2_test_deepseek_v4_pro_20260609_193524",
    }
    
    for version_name, run_dir in versions.items():
        print(f"\n {version_name}")
        
        if not run_dir.exists():
            print(f"     directory not found: {run_dir}")
            continue
        
                     
        results_file = None
        for f in run_dir.glob("results*.jsonl"):
            results_file = f
            break
        
        if not results_file:
            print(f"     not found:resultsfile")
            continue
        
        results = load_jsonl(results_file)
        if not results:
            print(f"     no result data")
            continue
        
                                  
        called_list = []
        for r in results:
            if "n_calls" in r:
                called_list.append(r["n_calls"])
        
        pass_count = sum(1 for r in results if r.get("pass") or r.get("passed") or r.get("correct"))
        
        print(f"   totalcase count: {len(results)}")
        print(f"   pass count: {pass_count}")
        print(f"   pass rate: {pass_count/len(results)*100:.1f}%")
        
        if called_list:
            print(f"    average function calls: {sum(called_list)/len(called_list):.1f}")
            print(f"   max function calls: {max(called_list)}")
            print(f"   min function calls: {min(called_list)}")
            
                                 
            over_explore = [c for c in called_list if c > 20]
            if over_explore:
                print(f"     over-explorationcase count(>20 calls): {len(over_explore)}")
        else:
            print(f"     no function-call count data found")

if __name__ == "__main__":
    analyze_alfworld()
    analyze_spreadsheet()
    analyze_bfcl()
    
    print("\n" + "=" * 80)
    print("summary comparison")
    print("=" * 80)
    print("\n stats done！")
    print("\nkey comparison dimensions: ")
    print("1. ALFWorld: v0 vs v2  average n_turns (succeeded/failure groups)")
    print("2. SpreadSheet: no_skill vs v1  average n_turns (Hardpassed/failure groups)")
    print("3. BFCL: no_skill vs v2 average function calls (with over-exploration stats)")
