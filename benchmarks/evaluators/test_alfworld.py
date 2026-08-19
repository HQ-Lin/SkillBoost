#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import threading
import concurrent.futures
import multiprocessing as mp
from datetime import datetime
from pathlib import Path

                                           
                                                                         
                                           
                                
_ENV_LOCK = threading.Lock()

sys.path.insert(0, str(Path(__file__).parent))
from alfworld_env import AlfredSingleEnv, ObsBuilder, alfworld_projection, get_task_type, TASKS              
from provider import (
    sync_chat_completion,
    openai_compatible_api_key,
    openai_compatible_provider_label,
    provider_model,
)

MODEL_CONFIG = {
    "model_name": "qwen3.6-plus",
    "api_key_env": "LLM_API_KEY",
}

SYSTEM_PROMPT = """You are an expert agent operating in the ALFRED Embodied Environment.

Output Format:
For each step, please provide your reasoning in <think>...</think> tags, then output your action in <action>...</action> tags.

Example:
<think>
Subgoal: find and pick up the apple
Next step: go to countertop 1 to search
</think>
<action>go to countertop 1</action>

Tips:
- When searching for objects, track which locations you've already checked
- For "pick two X" tasks, remember to find and place BOTH objects
- For heat/cool/clean tasks, follow the standard sequence (find -> pick -> transform -> place)
- Avoid revisiting empty locations you've already checked"""

def _build_skill_prompt(skill_content: str) -> str:
    if not skill_content or not skill_content.strip():
        return ""
    return (
        "\n\n## Skill Knowledge\n"
        "Below is a skill document with learned strategies. "
        "Use these guidelines to inform your decisions:\n\n"
        f"{skill_content}\n"
    )

def _extract_action(text: str):
    m = re.search(r"<action>(.*?)</action>", text or "", re.DOTALL)
    return m.group(1).strip() if m else None

def _extract_think(text: str):
    m = re.search(r"<think>(.*?)</think>", text or "", re.DOTALL)
    return m.group(1).strip() if m else None

_GOTO_RE = re.compile(r"^go to (.+)$")

class ExplorationTracker:
    """explicit explorationstatus: auto tracecan  and case, per  stepsinjectnot explorationsingle .

    pure  harness layer (non- prompt/SKILL) enhance: from  admissible actions parsefull
    'go to X' , record, promptmodelprefertop not explorationposition.
    """

    def __init__(self):
        self.all_recep = set()
        self.visited = set()

    def observe_admissible(self, admissible):
        for a in admissible or []:
            m = _GOTO_RE.match(a.strip().lower())
            if m:
                self.all_recep.add(m.group(1).strip())

    def record_action(self, action, env_feedback):
        m = _GOTO_RE.match((action or "").strip().lower())
        if m and "nothing happens" not in (env_feedback or "").lower():
            self.visited.add(m.group(1).strip())

    def render(self) -> str:
        if not self.all_recep:
            return ""
        unvisited = sorted(self.all_recep - self.visited)
        visited = sorted(self.visited)
        nt = len(self.all_recep)
        lines = [
            "## Exploration Memory (auto-tracked by environment)",
            f"Visited {len(visited)}/{nt} locations: "
            + (", ".join(visited) if visited else "(none yet)") + ".",
        ]
        if unvisited:
            lines.append(
                f"NOT yet visited ({len(unvisited)}): " + ", ".join(unvisited) + "."
            )
            lines.append(
                "Tip: if you have not found the target object(s) yet, prefer going to a "
                "NOT-yet-visited location rather than revisiting explored ones."
            )
        else:
            lines.append("All reachable locations have been visited at least once.")
        return "\n".join(lines) + "\n"

def call_claude_cli_sync(user: str, model: str = "claude-opus-4-6") -> str:
    """Call claude -p CLI for a single completion (uses Claude Code auth, bypasses SDK restrictions)."""
    import subprocess

    cmd = [
        "claude", "-p",
        "--system-prompt", SYSTEM_PROMPT,
        "--model", model,
        "--bare",
        "--allowed-tools", "",
    ]
    last_err = None
    for retry in range(5):
        try:
            proc = subprocess.run(
                cmd, input=user, capture_output=True, text=True, timeout=300,
            )
            if proc.returncode != 0:
                err = proc.stderr.strip()
                if "429" in err or "rate" in err.lower() or "overloaded" in err.lower():
                    last_err = RuntimeError(err)
                    time.sleep(8 * (retry + 1))
                    continue
                raise RuntimeError(f"claude cli error (rc={proc.returncode}): {err}")
            return proc.stdout.strip()
        except subprocess.TimeoutExpired:
            last_err = RuntimeError("claude cli timeout 300s")
            time.sleep(2 * (retry + 1))
        except Exception as e:                
            last_err = e
            time.sleep(2 * (retry + 1))
    raise RuntimeError(f"claude cli call failed: {last_err}")

def call_anthropic_http_sync(user: str, api_key: str, base_url: str, max_tokens: int = 4096, model: str = "claude-opus-4-6") -> tuple:
    """Call Anthropic Messages API via HTTP (supports provider-router gateway)."""
    import httpx

    url = f"{base_url.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
    }
    last_err = None
    for retry in range(5):
        try:
            with httpx.Client(timeout=300.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                                                                                                
                content = data["content"][0]["text"] if data.get("content") else ""
                usage = data.get("usage", {})
                return content, usage
        except Exception as e:                
            last_err = e
            es = str(e)
            if "429" in es or "Throttling" in es.lower() or "rate" in es.lower() or "overloaded" in es.lower():
                time.sleep(8 * (retry + 1))
                continue
            time.sleep(2 * (retry + 1))
    raise RuntimeError(f"anthropic http call failed: {last_err}")

def call_llm_api_sync(user: str, api_key: str, max_tokens: int = 4096, model: str = None, enable_thinking: bool = False) -> tuple:
    import httpx

    payload = {
        "model": model or MODEL_CONFIG["model_name"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
        "max_tokens": max_tokens,
        "enable_thinking": enable_thinking,
    }
    last_err = None
    for retry in range(5):
        try:
            with httpx.Client(timeout=300.0) as client:
                data = sync_chat_completion(client, payload, api_key=api_key)
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return content, usage
        except Exception as e:                
            last_err = e
            es = str(e)
            if "429" in es or "Throttling" in es.lower() or "rate" in es.lower():
                time.sleep(8 * (retry + 1))
                continue
            time.sleep(2 * (retry + 1))
    raise RuntimeError(f"openai_compatible call failed: {last_err}")

def run_episode(task: dict) -> dict:
    """at sub processesin run one  full episode. task with  gamefile/id/task_type/skill_content  etc. """
    gamefile = task["gamefile"]
    task_id = task["id"]
    task_type = task.get("task_type") or get_task_type(gamefile)
    skill_content = task["skill_content"]
    max_steps = task["max_steps"]
    traces_dir = Path(task["traces_dir"])
    api_key = task["api_key"]
    base_url = task.get("base_url", "")
    seed = task.get("seed", 42)
    max_tokens = task.get("max_tokens", 16384)
    tracker = ExplorationTracker() if task.get("exploration") else None

    skill_prompt = _build_skill_prompt(skill_content)
    t0 = time.time()
    conversation = []
    won = False
    done = False
    task_desc = ""
    fail_reason = ""
    error = ""

    try:
        with _ENV_LOCK:
            env = AlfredSingleEnv(gamefile, seed=seed)
            obs, admissible = env.reset()
        ob = ObsBuilder(history_length=2)
        ob.set_task(obs)
        task_desc = ob.task

        for step_idx in range(max_steps):
            if tracker:
                tracker.observe_admissible(admissible)
            prompt_obs = ob.build(obs, admissible, init=(step_idx == 0))
            exp_block = tracker.render() if tracker else ""
            parts = []
            if skill_prompt:
                parts.append(skill_prompt)
            if exp_block:
                parts.append(exp_block)
            parts.append(prompt_obs)
            user = "\n".join(parts)
            try:
                if task.get("backend") == "anthropic":
                    response, usage = call_anthropic_http_sync(
                        user, api_key, base_url,
                        max_tokens=max_tokens,
                        model=task.get("model") or "claude-opus-4-6",
                    )
                else:
                    response, usage = call_llm_api_sync(user, api_key, max_tokens=max_tokens, model=task.get("model"), enable_thinking=False)
            except Exception as e:                
                response = "<think>api error</think><action>look</action>"
                error = str(e)
                usage = {}
            response = (response or "").strip()

            action = _extract_action(response)
            think = _extract_think(response)
            _, valid = alfworld_projection(response)
            if not action:
                action = "look"
            action = action.lower()

            prev_obs = obs
            with _ENV_LOCK:
                obs, admissible, done, won = env.step(action)
            if tracker:
                tracker.record_action(action, obs)

            ob.record(prev_obs, action)
            conversation.append({
                "step": step_idx,
                "observation": prev_obs,
                "n_admissible": len(admissible),
                "think": think,
                "action": action,
                "valid": valid,
                "model_response": response,
                "env_feedback": obs,
                "done": done,
                "won": won,
                "usage": usage,
            })
            if done:
                break

        if not won:
            fail_reason = (
                f"Timeout after {max_steps} steps" if not done
                else "Episode ended without completing the task"
            )
    except Exception as e:                
        error = f"{type(e).__name__}: {e}"
        fail_reason = "env/runtime error"

    n_turns = len(conversation)
    trace = {
        "id": task_id,
        "task_type": task_type,
        "gamefile": gamefile,
        "task_description": task_desc,
        "hard": 1 if won else 0,
        "won": won,
        "n_turns": n_turns,
        "fail_reason": fail_reason,
        "error": error,
        "steps": conversation,
        "elapsed": round(time.time() - t0, 1),
        "timestamp": datetime.now().isoformat(),
    }
    (traces_dir / f"trace_{task_id}.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    icon = ""if won else ""
    print(f"  {task_id} [{task_type}]: {icon} won={won} turns={n_turns} "
          f"{fail_reason}{(' ERR:'+error) if error else ''}", flush=True)

    return {
        "id": task_id,
        "task_type": task_type,
        "gamefile": gamefile,
        "task_description": task_desc,
        "hard": 1 if won else 0,
        "won": won,
        "n_turns": n_turns,
        "fail_reason": fail_reason,
        "error": error,
        "agent": "error" if error else "ok",
    }

def main():
    parser = argparse.ArgumentParser(description="ALFWorld  - batchevaluation")
    parser.add_argument("--data", "-d", required=True, help="datasetpath (.jsonl) ")
    parser.add_argument("--skill", "-s", required=True, help="Skill directorypath")
    parser.add_argument("--max-steps", type=int, default=50, dest="max_steps")
    parser.add_argument("--max-tokens", type=int, default=16384, dest="max_tokens")
    parser.add_argument("--exploration", action="store_true", help="use explicit explorationstatusinject")
    parser.add_argument("--workers", "-w", type=int, default=6, help="concurrency episode processes count")
    parser.add_argument("--limit", "-l", type=int, default=0, help="only test top  N  items (0=full ) ")
    parser.add_argument("--filter-ids", "-f", nargs="*", default=[], dest="filter_ids")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="qwen3.6-plus", help="OpenAI-compatible modelname (like  qwen3.7-max) ")
    parser.add_argument("--output-base", "-o", default="", dest="output_base")
    parser.add_argument("--backend", choices=["openai_compatible", "anthropic"], default="openai_compatible",
                        help="LLM backend: openai_compatible (OpenAI-compatible/qwen)  or  anthropic (Anthropic Messages API) ")
    parser.add_argument("--executor", choices=["process", "thread"], default="process",
                        help="concurrencyexecutor: process=multi-processes(requires POSIXsemaphore)；thread=multi-thread(no semaphore, can stable in backgroundrun )")
    args = parser.parse_args()
    args.model = provider_model(args.model)

    project_root = Path(__file__).parent.parent
    if not Path(args.data).is_absolute():
        args.data = str(project_root / args.data)
    if not Path(args.skill).is_absolute():
        args.skill = str(project_root / args.skill)

    print("=" * 70)
    print("ALFWorld embodied agent solving - evaluation")
    print("=" * 70)

    if args.backend == "anthropic":
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        if not api_key:
            print("environment variable ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY not set")
            sys.exit(1)
    else:
        api_key = openai_compatible_api_key(MODEL_CONFIG["api_key_env"])
        base_url = ""

    skill_file = Path(args.skill) / "SKILL.md"
    if not skill_file.exists():
        print(f"Skill file not found: {skill_file}")
        sys.exit(1)
    skill_content = skill_file.read_text(encoding="utf-8")
    if skill_content.startswith("---"):
        end_idx = skill_content.find("---", 3)
        if end_idx != -1:
            skill_content = skill_content[end_idx + 3:].strip()
    print(f"Skill: {args.skill}")
    provider_label = (
        "anthropic" if args.backend == "anthropic" else openai_compatible_provider_label()
    )
    print(f"model: {provider_label} / {args.model}")

    cases = []
    with open(args.data, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if args.filter_ids:
        cases = [c for c in cases if c["id"] in args.filter_ids]
    if args.limit > 0:
        cases = cases[:args.limit]
    print(f"data: {len(cases)} games from {args.data}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output_base) if args.output_base else (project_root / "evolved" / "alfworld-solver")
    if not output_base.is_absolute():
        output_base = project_root / output_base
    dataset_name = Path(args.data).stem
    run_dir = output_base / f"{dataset_name}_run_{timestamp}"
    evals_dir = run_dir / "evals"
    traces_dir = run_dir / "traces"
    evals_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    print(f"output: {run_dir}")
    print(f"concurrencyprocesses: {args.workers}  | max_steps: {args.max_steps} | "
          f"max_tokens: {args.max_tokens} | exploration: {args.exploration}")

    tasks = [{
        "gamefile": c["gamefile"],
        "id": c["id"],
        "task_type": c.get("task_type"),
        "skill_content": skill_content,
        "max_steps": args.max_steps,
        "max_tokens": args.max_tokens,
        "exploration": args.exploration,
        "traces_dir": str(traces_dir),
        "api_key": api_key,
        "base_url": base_url,
        "backend": args.backend,
        "seed": args.seed,
        "model": args.model,
    } for c in cases]

    start = time.time()
    results = []
    if args.executor == "thread":
        print(f"executor: ThreadPoolExecutor (no semaphore, stable in background) ")
        pool_cm = concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
    else:
        print(f"executor: ProcessPoolExecutor (spawn, requires POSIXsemaphore) ")
        ctx = mp.get_context("spawn")
        pool_cm = concurrent.futures.ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx)
    with pool_cm as ex:
        futs = {ex.submit(run_episode, t): t["id"] for t in tasks}
        for fut in concurrent.futures.as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as e:                
                tid = futs[fut]
                print(f"  {tid}:  worker crash - {e}", flush=True)
                results.append({"id": tid, "task_type": "other", "hard": 0, "won": False,
                                "n_turns": 0, "fail_reason": "worker crash", "error": str(e),
                                "agent": "error"})
    elapsed = time.time() - start

    total = len(results)
    won_count = sum(r["hard"] for r in results)
    error_count = sum(1 for r in results if r["agent"] == "error")
    sr = won_count / total * 100 if total else 0

    type_stats = {}
    for r in results:
        t = r.get("task_type", "other")
        type_stats.setdefault(t, [0, 0])
        type_stats[t][1] += 1
        type_stats[t][0] += r["hard"]

    print(f"\n  elapsed: {elapsed:.1f}s")
    print("=" * 70)
    print("evaluation results:")
    print("=" * 70)
    print(f"  total game  count: {total}")
    print(f"  execution exception: {error_count}")
    print(f"  ──────────────────────")
    print(f"  success rate (Success Rate) : {sr:.1f}% ({won_count}/{total})")
    print(f"\n  by task typegrouped success rate:")
    for t in TASKS + ["other"]:
        if t in type_stats:
            c, n = type_stats[t]
            print(f"    {t}: {c}/{n} ({c/n*100:.0f}%)")

    fails = [r for r in results if not r["hard"]]
    if fails:
        print(f"\n failed game ({len(fails)} ):")
        for w in fails:
            print(f"  {w['id']} [{w['task_type']}]: turns={w['n_turns']} {w['fail_reason']}")

    result_file = evals_dir / f"results_{dataset_name}_{timestamp}.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": f"{provider_label}/{args.model}",
        "skill_path": str(args.skill),
        "data_path": str(args.data),
        "max_steps": args.max_steps,
        "max_tokens": args.max_tokens,
        "exploration": args.exploration,
        "total": total,
        "error_count": error_count,
        "won_count": won_count,
        "success_rate": round(sr, 2),
        "type_success_rate": {t: round(type_stats[t][0] / type_stats[t][1] * 100, 1)
                              for t in type_stats},
        "fail_ids": [w["id"] for w in fails],
        "elapsed_seconds": round(elapsed, 1),
        "results_file": str(result_file),
        "traces_dir": str(traces_dir),
        "run_dir": str(run_dir),
    }
    summary_file = evals_dir / f"report_{dataset_name}_{timestamp}.json"
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n results: {result_file}")
    print(f"report: {summary_file}")
    print("=" * 70)
    return summary

if __name__ == "__main__":
    main()
