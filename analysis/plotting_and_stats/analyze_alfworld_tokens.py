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

def analyze_tokens(traces_dir: Path):
    """analysisspecified directoryall trace file  token use case. """
    trace_files = sorted(traces_dir.glob("trace_*.json"))
    
    if not trace_files:
        print(f"not found: trace file: {traces_dir}")
        return
    
    print(f"found {len(trace_files)}   trace file")
    print("=" * 80)
    
          
    total_episodes = 0
    total_turns = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    
    episode_stats = []
    turn_stats_by_step = defaultdict(list)               
    task_type_stats = defaultdict(lambda: {
        "episodes": 0, "turns": 0, 
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
    })
    
    for trace_file in trace_files:
        trace = load_trace(trace_file)
        total_episodes += 1
        
        episode_id = trace.get("id", "unknown")
        task_type = trace.get("task_type", "unknown")
        won = trace.get("won", False)
        n_turns = trace.get("n_turns", 0)
        steps = trace.get("steps", [])
        
        episode_prompt_tokens = 0
        episode_completion_tokens = 0
        episode_total_tokens = 0
        
                         
        for step in steps:
            step_idx = step.get("step", 0)
            
                            
            usage = step.get("usage", {})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                step_total = usage.get("total_tokens", 0)
                
                episode_prompt_tokens += prompt_tokens
                episode_completion_tokens += completion_tokens
                episode_total_tokens += step_total
                
                turn_stats_by_step[step_idx].append({
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": step_total,
                    "episode_id": episode_id,
                    "won": won
                })
        
                            
        if episode_prompt_tokens == 0 and steps:
            print(f"  {episode_id}: not found: token usage info missing, modify the eval script to record it usage")
                                         
        
        total_turns += len(steps)
        total_prompt_tokens += episode_prompt_tokens
        total_completion_tokens += episode_completion_tokens
        total_tokens += episode_total_tokens
        
        episode_stats.append({
            "id": episode_id,
            "task_type": task_type,
            "won": won,
            "n_turns": len(steps),
            "prompt_tokens": episode_prompt_tokens,
            "completion_tokens": episode_completion_tokens,
            "total_tokens": episode_total_tokens
        })
        
                 
        task_type_stats[task_type]["episodes"] += 1
        task_type_stats[task_type]["turns"] += len(steps)
        task_type_stats[task_type]["prompt_tokens"] += episode_prompt_tokens
        task_type_stats[task_type]["completion_tokens"] += episode_completion_tokens
        task_type_stats[task_type]["total_tokens"] += episode_total_tokens
    
            
    print("\n overall stats:")
    print("=" * 80)
    print(f"total episode  count: {total_episodes}")
    print(f"total reasoning turns: {total_turns}")
    print(f"total prompt tokens: {total_prompt_tokens:,}")
    print(f"total completion tokens: {total_completion_tokens:,}")
    print(f"total tokens: {total_tokens:,}")
    
    if total_turns > 0:
        print(f"avg per turn prompt tokens: {total_prompt_tokens/total_turns:.1f}")
        print(f"avg per turn completion tokens: {total_completion_tokens/total_turns:.1f}")
        print(f"avg per-turn total tokens: {total_tokens/total_turns:.1f}")
    
    if total_episodes > 0:
        print(f"avg per  episode prompt tokens: {total_prompt_tokens/total_episodes:.1f}")
        print(f"avg per  episode completion tokens: {total_completion_tokens/total_episodes:.1f}")
        print(f"avg per  episode total tokens: {total_tokens/total_episodes:.1f}")
    
             
    print("\n stats by task type:")
    print("=" * 80)
    print(f"{'task type':<25} {'Episodes':>8} {'total turns':>6} {'totalTokens':>12} {'avg per turn':>10}")
    print("-" * 80)
    
    for task_type, stats in sorted(task_type_stats.items()):
        if stats["total_tokens"] > 0:                  
            avg_per_turn = stats["total_tokens"] / stats["turns"] if stats["turns"] > 0 else 0
            print(f"{task_type:<25} {stats['episodes']:>8} {stats['turns']:>6} "
                  f"{stats['total_tokens']:>12,} {avg_per_turn:>10.1f}")
    
                 
    print("\n stats by reasoning step (top 20 steps):")
    print("=" * 80)
    print(f"{'Step':>4} {'call count':>8} {'avgPrompt':>12} {'avgCompletion':>14} {'avgTotal':>12}")
    print("-" * 80)
    
    for step_idx in range(min(20, max(turn_stats_by_step.keys()) + 1 if turn_stats_by_step else 0)):
        if step_idx in turn_stats_by_step:
            step_data = turn_stats_by_step[step_idx]
            count = len(step_data)
            avg_prompt = sum(d["prompt_tokens"] for d in step_data) / count
            avg_completion = sum(d["completion_tokens"] for d in step_data) / count
            avg_total = sum(d["total_tokens"] for d in step_data) / count
            print(f"{step_idx:>4} {count:>8} {avg_prompt:>12.1f} {avg_completion:>14.1f} {avg_total:>12.1f}")
    
                         
    print("\n succeeded vs failed Episode comparison:")
    print("=" * 80)
    
    won_episodes = [e for e in episode_stats if e["won"]]
    lost_episodes = [e for e in episode_stats if not e["won"]]
    
    if won_episodes:
        won_total_tokens = sum(e["total_tokens"] for e in won_episodes)
        won_turns = sum(e["n_turns"] for e in won_episodes)
        print(f"succeeded ({len(won_episodes)} episodes):")
        print(f"   total tokens: {won_total_tokens:,}")
        print(f"   avg per  episode: {won_total_tokens/len(won_episodes):,.1f}")
        print(f"   avg per turn: {won_total_tokens/won_turns:,.1f}" if won_turns > 0 else "   avg per turn: N/A")
    
    if lost_episodes:
        lost_total_tokens = sum(e["total_tokens"] for e in lost_episodes)
        lost_turns = sum(e["n_turns"] for e in lost_episodes)
        print(f"failed ({len(lost_episodes)} episodes):")
        print(f"   total tokens: {lost_total_tokens:,}")
        print(f"   avg per  episode: {lost_total_tokens/len(lost_episodes):,.1f}")
        print(f"   avg per turn: {lost_total_tokens/lost_turns:,.1f}" if lost_turns > 0 else "   avg per turn: N/A")

def main():
    parser = argparse.ArgumentParser(description="stats ALFWorld task in per roundreasoning  token consumption")
    parser.add_argument("--traces-dir", required=True, help="Trace filedirectorypath")
    args = parser.parse_args()
    
    traces_dir = Path(args.traces_dir)
    if not traces_dir.exists():
        print(f"directory not found: {traces_dir}")
        sys.exit(1)
    
    analyze_tokens(traces_dir)

if __name__ == "__main__":
    main()