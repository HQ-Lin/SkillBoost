#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

INTERACT = ["take", "put", "heat", "cool", "clean", "use", "open", "close", "toggle"]

def load_traces(run_dir: Path):
    tdir = run_dir / "traces"
    traces = []
    for p in sorted(tdir.glob("trace_*.json")):
        traces.append(json.load(open(p, encoding="utf-8")))
    return traces

def longest_repeat_cycle(actions):
    """detect: returned  (cycle_len, repeats) tableshow length as  L  columnat repeat R  times. """
    n = len(actions)
    best = (0, 0)
    for L in range(1, n // 2 + 1):
        block = actions[-L:]
        repeats = 1
        i = n - 2 * L
        while i >= 0 and actions[i:i + L] == block:
            repeats += 1
            i -= L
        if repeats >= 2 and L * repeats > best[0] * max(best[1], 1):
            best = (L, repeats)
    return best

def diagnose(trace):
    steps = trace.get("steps", [])
    actions = [s["action"] for s in steps]
    feedbacks = [s.get("env_feedback", "") for s in steps]
    verbs = Counter()
    for a in actions:
        head = a.split()[0] if a.split() else ""
        verbs[head] += 1
    nothing = sum(1 for f in feedbacks if "Nothing happens" in f)
    invalid = sum(1 for s in steps if not s.get("valid"))
    visited = set()
    for a in actions:
        m = re.match(r"go to (.+)", a)
        if m:
            visited.add(m.group(1))
    cyc_len, cyc_rep = longest_repeat_cycle(actions)
    did_take = verbs.get("take", 0) > 0
    did_put = verbs.get("put", 0) > 0
    return {
        "id": trace["id"],
        "task_type": trace.get("task_type"),
        "task": trace.get("task_description"),
        "won": trace.get("won"),
        "n_turns": trace.get("n_turns"),
        "fail_reason": trace.get("fail_reason"),
        "verbs": dict(verbs),
        "nothing_happens": nothing,
        "invalid_actions": invalid,
        "visited_receptacles": len(visited),
        "cycle_len": cyc_len,
        "cycle_repeats": cyc_rep,
        "did_take": did_take,
        "did_put": did_put,
        "last_actions": actions[-6:],
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_alfworld.py <run_dir>")
        sys.exit(1)
    run_dir = Path(sys.argv[1])
    if not run_dir.is_absolute():
        run_dir = Path(__file__).parent.parent / run_dir
    traces = load_traces(run_dir)
    total = len(traces)
    won = sum(1 for t in traces if t.get("won"))
    print(f"== RUN: {run_dir.name} ==")
    print(f"total {total}  succeeded {won}  success rate {won/total*100:.1f}%\n")

    clusters = defaultdict(list)
    diags = [diagnose(t) for t in traces]
    for d in diags:
        if d["won"]:
            continue
                
        if d["cycle_repeats"] >= 3:
            clusters["dead (repeat≥3 times)"].append(d)
        elif not d["did_take"]:
            clusters["from not take (explorationfailed/find not to target)"].append(d)
        elif d["did_take"] and not d["did_put"]:
            clusters["take to but from not (changeswap /)"].append(d)
        else:
            clusters["(take has but not target items)"].append(d)

    print("=== failure mode clustering ===")
    for name, items in sorted(clusters.items(), key=lambda x: -len(x[1])):
        print(f"\n【{name}】 {len(items)}  ")
        for d in items:
            print(f"  - {d['id']} [{d['task_type']}] turns={d['n_turns']} "
                  f"visited={d['visited_receptacles']} cycle={d['cycle_len']}x{d['cycle_repeats']} "
                  f"nothing={d['nothing_happens']} verbs={d['verbs']}")
            print(f"      task: {d['task']}")
            print(f"      last: {d['last_actions']}")

    print("\n=== success rate by task type ===")
    bt = defaultdict(lambda: [0, 0])
    for t in traces:
        tt = t.get("task_type", "other")
        bt[tt][1] += 1
        bt[tt][0] += 1 if t.get("won") else 0
    for tt, (c, n) in sorted(bt.items()):
        print(f"  {tt}: {c}/{n} ({c/n*100:.0f}%)")

if __name__ == "__main__":
    main()
