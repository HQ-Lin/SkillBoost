#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

def load_trace(trace_path: Path) -> dict:
    """loadsingle   trace file. """
    with open(trace_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_dataset(traces_dir: Path, dataset_name: str):
    """analysisspecified dataset  token use case. """
    trace_files = sorted(traces_dir.glob("trace_*.json"))
    
    if not trace_files:
        print(f"not found: trace file: {traces_dir}")
        return None
    
    print(f" {dataset_name}: found {len(trace_files)}   trace file")
    print("=" * 80)
    
    total_cases = 0
    total_turns = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    
    success_cases = 0
    success_turns = 0
    success_tokens = 0
    
    failed_cases = 0
    failed_turns = 0
    failed_tokens = 0
    
    turn_stats = defaultdict(list)
    
    for trace_file in trace_files:
        trace = load_trace(trace_file)
        total_cases += 1
        
                      
        won = trace.get("won") or trace.get("hard") or trace.get("pass") or trace.get("passed") or trace.get("em")
        if isinstance(won, bool):
            is_success = won
        else:
            is_success = bool(won)
        
                                  
                                        
                                                   
        usage = trace.get("usage", {})
        steps = trace.get("steps") or trace.get("turns") or []
        conversation = trace.get("conversation", [])
        
        case_tokens = 0
        case_turns = len(steps) if steps else (len(conversation) // 2 if conversation else 1)                
        
        if usage:
                            
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            step_total = usage.get("total_tokens", 0)
            
            case_tokens = step_total
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += step_total
            
            turn_stats[1].append(step_total)
        elif steps:
                            
            for i, step in enumerate(steps):
                step_usage = step.get("usage", {})
                if step_usage:
                    prompt_tokens = step_usage.get("prompt_tokens", 0)
                    completion_tokens = step_usage.get("completion_tokens", 0)
                    step_total = step_usage.get("total_tokens", 0)
                    
                    case_tokens += step_total
                    total_prompt_tokens += prompt_tokens
                    total_completion_tokens += completion_tokens
                    total_tokens += step_total
                    
                    turn_stats[i + 1].append(step_total)
        elif conversation:
                                                                      
            turn_idx = 0
            for msg in conversation:
                if msg.get("role") == "assistant" and "usage" in msg:
                    step_usage = msg.get("usage", {})
                    prompt_tokens = step_usage.get("prompt_tokens", 0)
                    completion_tokens = step_usage.get("completion_tokens", 0)
                    step_total = step_usage.get("total_tokens", 0)
                    
                    case_tokens += step_total
                    total_prompt_tokens += prompt_tokens
                    total_completion_tokens += completion_tokens
                    total_tokens += step_total
                    
                    turn_idx += 1
                    turn_stats[turn_idx].append(step_total)
        
        total_turns += case_turns
        
        if is_success:
            success_cases += 1
            success_turns += case_turns
            success_tokens += case_tokens
        else:
            failed_cases += 1
            failed_turns += case_turns
            failed_tokens += case_tokens
    
            
    print(f"\n {dataset_name} overall stats:")
    print("=" * 80)
    print(f"total case  count: {total_cases}")
    print(f"total reasoning turns: {total_turns}")
    print(f"total prompt tokens: {total_prompt_tokens:,}")
    print(f"total completion tokens: {total_completion_tokens:,}")
    print(f"total tokens: {total_tokens:,}")
    
    if total_turns > 0:
        print(f"avg per turn prompt tokens: {total_prompt_tokens/total_turns:.1f}")
        print(f"avg per turn completion tokens: {total_completion_tokens/total_turns:.1f}")
        print(f"avg per-turn total tokens: {total_tokens/total_turns:.1f}")
    
    if total_cases > 0:
        print(f"avg per  case prompt tokens: {total_prompt_tokens/total_cases:.1f}")
        print(f"avg per  case completion tokens: {total_completion_tokens/total_cases:.1f}")
        print(f"avg per  case total tokens: {total_tokens/total_cases:.1f}")
        print(f"success rate: {success_cases/total_cases*100:.1f}% ({success_cases}/{total_cases})")
    
                
    print(f"\n succeeded vs failed Case comparison:")
    print("=" * 80)
    
    if success_cases > 0:
        print(f"succeeded ({success_cases} cases):")
        print(f"   total tokens: {success_tokens:,}")
        print(f"   avg per  case: {success_tokens/success_cases:,.1f}")
        if success_turns > 0:
            print(f"   avg per turn: {success_tokens/success_turns:,.1f}")
    
    if failed_cases > 0:
        print(f"failed ({failed_cases} cases):")
        print(f"   total tokens: {failed_tokens:,}")
        print(f"   avg per  case: {failed_tokens/failed_cases:,.1f}")
        if failed_turns > 0:
            print(f"   avg per turn: {failed_tokens/failed_turns:,.1f}")
    
                 
    if turn_stats:
        print(f"\n stats by reasoning turn (top 10 turns):")
        print("=" * 80)
        print(f"{'Turn':>4} {'call count':>8} {'avgTokens':>12}")
        print("-" * 80)
        
        for turn_idx in range(1, min(11, max(turn_stats.keys()) + 1)):
            if turn_idx in turn_stats:
                turn_data = turn_stats[turn_idx]
                count = len(turn_data)
                avg_tokens = sum(turn_data) / count
                print(f"{turn_idx:>4} {count:>8} {avg_tokens:>12,.1f}")
    
    return {
        "dataset": dataset_name,
        "total_cases": total_cases,
        "success_cases": success_cases,
        "failed_cases": failed_cases,
        "success_rate": success_cases / total_cases * 100 if total_cases > 0 else 0,
        "total_turns": total_turns,
        "total_tokens": total_tokens,
        "avg_tokens_per_case": total_tokens / total_cases if total_cases > 0 else 0,
        "avg_tokens_per_turn": total_tokens / total_turns if total_turns > 0 else 0,
        "success_avg_tokens": success_tokens / success_cases if success_cases > 0 else 0,
        "failed_avg_tokens": failed_tokens / failed_cases if failed_cases > 0 else 0,
    }

def main():
    parser = argparse.ArgumentParser(description="unified multi-dataset token consumptionanalysisscript")
    parser.add_argument("--dataset", required=True, help="datasetnamename (livemath, bfcl, spreadsheet, alfworld)")
    parser.add_argument("--traces-dir", required=True, help="Trace filedirectorypath")
    args = parser.parse_args()
    
    traces_dir = Path(args.traces_dir)
    if not traces_dir.exists():
        print(f"directory not found: {traces_dir}")
        sys.exit(1)
    
    result = analyze_dataset(traces_dir, args.dataset)
    
    if result:
        print(f"\n {args.dataset} analysisdone！")

if __name__ == "__main__":
    main()
