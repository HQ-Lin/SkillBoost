#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from collections import defaultdict

def load_trace(trace_path: Path) -> dict:
    """loadsingle   trace file. """
    with open(trace_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_version(traces_dir: Path, version_name: str):
    """analysissingle  version  token use case. """
    trace_files = sorted(traces_dir.glob("trace_*.json"))
    
    if not trace_files:
        print(f"  {version_name}: not found: trace file")
        return None
    
    total_episodes = len(trace_files)
    total_turns = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    
    won_episodes = 0
    won_turns = 0
    won_tokens = 0
    
    lost_episodes = 0
    lost_turns = 0
    lost_tokens = 0
    
    task_type_stats = defaultdict(lambda: {
        "episodes": 0, "turns": 0, "tokens": 0, "won": 0
    })
    
    for trace_file in trace_files:
        trace = load_trace(trace_file)
        won = trace.get("won", False)
        task_type = trace.get("task_type", "unknown")
        steps = trace.get("steps", [])
        
        episode_tokens = 0
        for step in steps:
            usage = step.get("usage", {})
            episode_tokens += usage.get("total_tokens", 0)
        
        total_turns += len(steps)
        total_prompt_tokens += sum(step.get("usage", {}).get("prompt_tokens", 0) for step in steps)
        total_completion_tokens += sum(step.get("usage", {}).get("completion_tokens", 0) for step in steps)
        total_tokens += episode_tokens
        
        if won:
            won_episodes += 1
            won_turns += len(steps)
            won_tokens += episode_tokens
        else:
            lost_episodes += 1
            lost_turns += len(steps)
            lost_tokens += episode_tokens
        
        task_type_stats[task_type]["episodes"] += 1
        task_type_stats[task_type]["turns"] += len(steps)
        task_type_stats[task_type]["tokens"] += episode_tokens
        if won:
            task_type_stats[task_type]["won"] += 1
    
    return {
        "name": version_name,
        "total_episodes": total_episodes,
        "won_episodes": won_episodes,
        "lost_episodes": lost_episodes,
        "success_rate": won_episodes / total_episodes * 100 if total_episodes > 0 else 0,
        "total_turns": total_turns,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "avg_tokens_per_episode": total_tokens / total_episodes if total_episodes > 0 else 0,
        "avg_tokens_per_turn": total_tokens / total_turns if total_turns > 0 else 0,
        "won": {
            "episodes": won_episodes,
            "turns": won_turns,
            "tokens": won_tokens,
            "avg_tokens_per_episode": won_tokens / won_episodes if won_episodes > 0 else 0,
            "avg_tokens_per_turn": won_tokens / won_turns if won_turns > 0 else 0,
        },
        "lost": {
            "episodes": lost_episodes,
            "turns": lost_turns,
            "tokens": lost_tokens,
            "avg_tokens_per_episode": lost_tokens / lost_episodes if lost_episodes > 0 else 0,
            "avg_tokens_per_turn": lost_tokens / lost_turns if lost_turns > 0 else 0,
        },
        "task_types": dict(task_type_stats),
    }

def main():
                
    versions = {
        "v0 (baseline)": Path("evolved/alfworld-solver/test_run_20260604_104009/traces"),
        "v2 (best)": Path("evolved/alfworld-solver/test_run_20260604_154659/traces"),
    }
    
    print("=" * 100)
    print("ALFWorld different skill versions Token consumption comparison analysis")
    print("=" * 100)
    
    results = {}
    for version_name, traces_dir in versions.items():
        if traces_dir.exists():
            result = analyze_version(traces_dir, version_name)
            if result:
                results[version_name] = result
        else:
            print(f"  {version_name}: directory not found")
    
    if not results:
        print("no valid entries found for trace data")
        return
    
            
    print("\n overall comparison:")
    print("=" * 100)
    print(f"{'version':<20} {'success rate':>8} {'totalEpisodes':>10} {'totalTokens':>12} {'avg per Episode':>14} {'avg per Turn':>12}")
    print("-" * 100)
    
    for version_name, stats in results.items():
        print(f"{version_name:<20} {stats['success_rate']:>7.1f}% {stats['total_episodes']:>10} "
              f"{stats['total_tokens']:>12,} {stats['avg_tokens_per_episode']:>14,.1f} "
              f"{stats['avg_tokens_per_turn']:>12,.1f}")
    
                
    print("\n succeeded vs failed Episode Token comparison:")
    print("=" * 100)
    
    for version_name, stats in results.items():
        print(f"\n{version_name}:")
        if stats["won"]["episodes"] > 0:
            print(f"   succeeded ({stats['won']['episodes']} episodes): "
                  f"avg {stats['won']['avg_tokens_per_episode']:,.1f} tokens/episode, "
                  f"{stats['won']['avg_tokens_per_turn']:,.1f} tokens/turn")
        if stats["lost"]["episodes"] > 0:
            print(f"   failed ({stats['lost']['episodes']} episodes): "
                  f"avg {stats['lost']['avg_tokens_per_episode']:,.1f} tokens/episode, "
                  f"{stats['lost']['avg_tokens_per_turn']:,.1f} tokens/turn")
    
             
    print("\n by task type Token consumption comparison:")
    print("=" * 100)
    
    all_task_types = set()
    for stats in results.values():
        all_task_types.update(stats["task_types"].keys())
    
    print(f"{'task type':<30} ", end="")
    for version_name in results.keys():
        print(f"{version_name:<20} ", end="")
    print()
    print("-" * 100)
    
    for task_type in sorted(all_task_types):
        print(f"{task_type:<30} ", end="")
        for version_name, stats in results.items():
            if task_type in stats["task_types"]:
                tt_stats = stats["task_types"][task_type]
                avg_tokens = tt_stats["tokens"] / tt_stats["turns"] if tt_stats["turns"] > 0 else 0
                print(f"{avg_tokens:>10.1f}/turn ", end="")
            else:
                print(f"{'N/A':>20} ", end="")
        print()
    
             
    if len(results) >= 2:
        print("\n cross-version comparison summary:")
        print("=" * 100)
        
        version_names = list(results.keys())
        v1_name, v2_name = version_names[0], version_names[-1]
        v1_stats, v2_stats = results[v1_name], results[version_names[-1]]
        
        token_diff = v2_stats["avg_tokens_per_episode"] - v1_stats["avg_tokens_per_episode"]
        token_diff_pct = (token_diff / v1_stats["avg_tokens_per_episode"] * 100 
                         if v1_stats["avg_tokens_per_episode"] > 0 else 0)
        
        sr_diff = v2_stats["success_rate"] - v1_stats["success_rate"]
        
        print(f"from  {v1_name} to  {v2_name}:")
        print(f"  success rate change: {sr_diff:+.1f}pp ({v1_stats['success_rate']:.1f}% → {v2_stats['success_rate']:.1f}%)")
        print(f"  avg per  episode token change: {token_diff:+,.1f} ({token_diff_pct:+.1f}%)")
        print(f"  avg per  turn token change: {v2_stats['avg_tokens_per_turn'] - v1_stats['avg_tokens_per_turn']:+,.1f}")
        
        if token_diff < 0 and sr_diff > 0:
            print("   skill optimization succeeded:  token consumption decreased while success rate improved！")
        elif token_diff > 0 and sr_diff > 0:
            print("    token consumption increased but success rate improved, weigh the cost-benefit")
        elif token_diff < 0 and sr_diff < 0:
            print("    token consumption decreased but success rate dropped, check skill quality")

if __name__ == "__main__":
    main()
