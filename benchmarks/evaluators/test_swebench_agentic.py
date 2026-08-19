#!/usr/bin/env python3
import argparse
import asyncio
import glob as _glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

                                                       
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_swebench import (              
    MODEL_CONFIG,
    PROJECT_ROOT,
    load_skill,
    load_dataset,
    extract_patch,
    fix_hunk_counts,
    load_existing_predictions,
    run_swebench_eval,
    parse_per_instance_status,
    build_results,
)
from provider import (
    async_chat_completion,
    openai_compatible_api_key,
    openai_compatible_provider_label,
    provider_model,
)

                                                         
                                  
                                                         
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Search for files matching a glob pattern in the repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py' or 'django/db/models/*.py'"}
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file content. Returns up to 200 lines at a time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path from repo root"},
                    "start_line": {"type": "integer", "description": "Starting line number (1-based, optional)"},
                    "end_line": {"type": "integer", "description": "Ending line number (inclusive, optional)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a text/regex pattern in repository files. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (supports regex)"},
                    "path": {"type": "string", "description": "Optional: limit search to this directory/file path"},
                    "max_results": {"type": "integer", "description": "Maximum results to return (default 20)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List directory contents with file types",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path relative to repo root (default: '.')"}
                },
                "required": [],
            },
        },
    },
]

          
MAX_READ_LINES = 200
MAX_SEARCH_RESULTS = 20
MAX_FIND_RESULTS = 50

                                                         
           
                                                         
SYSTEM_PROMPT_TEMPLATE = """\
You are an expert software engineer that resolves GitHub issues by producing a code patch.

{skill_content}

You have access to tools to explore the repository before writing the patch:
- find_files(pattern): locate files by glob pattern (e.g. '**/*.py').
- read_file(path, start_line, end_line): read up to 200 lines of a file from repo root.
- search_code(pattern, path, max_results): grep for a text/regex pattern across the repo.
- list_dir(path): list directory contents (dir/file types).

Workflow:
1. Use search_code / find_files to locate the code relevant to the issue.
2. Use read_file to inspect the exact functions/classes that must change.
3. Once you have located the precise edit, output a unified diff (git diff style) patch.

Output requirement: when you are ready, output ONLY the raw unified diff. Each file
section must start with `diff --git a/<path> b/<path>`, followed by `--- a/<path>`,
`+++ b/<path>` and `@@` hunks. Paths are relative to the repository root.
Do not include explanations or markdown fences in the final patch."""

USER_PROMPT_TEMPLATE = """\
## GitHub Issue

{problem_statement}

{hints_text}

repo: {repo}
benchmarkversion: {version}

first use toolexplorationrepo, locatecode, then generate fix this  Issue  patch.
final outputpure  unified diff format (diff --git ...) , not require with any other text. """

                             
NEAR_FINAL_PROMPT = """\
prompt: you have  {remaining}  turnstool callschances left. plan them well, donelocate and prepare outputpatch. """

FINAL_ROUND_PROMPT = """\
 this  is the last  turns, tool disableduse , you no then explorationrepo. base at grasp infooutputfinal patch.
only outputpure  unified diff (diff --git a/... b/..., with  --- / +++ / @@  lines) , not require  markdown guardrail, not require multi-extra text.
infonot full, also require give you most has confidence patch, not can outputemptycontent, not can request againcalltool. """

                                                         
                                           
                                                         
                                                
_repo_locks: dict = {}
_repo_locks_guard = asyncio.Lock()

async def _get_repo_lock(repo: str) -> asyncio.Lock:
    async with _repo_locks_guard:
        if repo not in _repo_locks:
            _repo_locks[repo] = asyncio.Lock()
        return _repo_locks[repo]

def _is_populated_bare(p: Path) -> bool:
    """judgedirectory is whether  as one  with for  bare repo (non-emptyshell) . """
    if not (p.exists() and (p / "HEAD").exists()):
        return False
    if (p / "packed-refs").exists():
        return True
    objects_pack = p / "objects" / "pack"
    if objects_pack.exists() and any(objects_pack.iterdir()):
        return True
    refs_heads = p / "refs" / "heads"
    if refs_heads.exists() and any(refs_heads.iterdir()):
        return True
    return False

def _bare_repo_path(repo: str, repo_dir: Path) -> Path:
    """bare repo path. preferuse store at  bare repo.

    candidate: specname <owner__repo>.git (like  django__django.git)  and
    basename <reponame>.git (like  django.git) . repocan can with  basename name,
     and failed  clone can can same nameemptyshell, only option“with for ” candidate.
    """
    safe = repo.replace("/", "__")
    canonical = repo_dir / f"{safe}.git"
    basename = repo_dir / f"{repo.split('/')[-1]}.git"
    for cand in (canonical, basename):
        if _is_populated_bare(cand):
            return cand
    return canonical

def ensure_bare_repo(repo: str, repo_dir: Path) -> Path:
    """local store at  bare repo (not foundthen from  GitHub clone --bare) . returned  bare repo path. """
    repo_dir.mkdir(parents=True, exist_ok=True)
    bare = _bare_repo_path(repo, repo_dir)
    if bare.exists() and (bare / "HEAD").exists():
        return bare
    url = f"https://github.com/{repo}.git"
    print(f"    clone bare repo: {url} -> {bare}", flush=True)
    proc = subprocess.run(
        ["git", "clone", "--bare", url, str(bare)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"clone bare repo failed {repo}: {proc.stderr[:300]}")
    return bare

def prepare_repo_worktree(bare_repo_path: Path, base_commit: str, worktree_path: Path) -> Path:
    """at specified  commit create detached worktree (use at single  instance) . """
    if worktree_path.exists():
                              
        cleanup_worktree(bare_repo_path, worktree_path)
    proc = subprocess.run(
        ["git", "--git-dir", str(bare_repo_path), "worktree", "add",
         "--detach", str(worktree_path), base_commit],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"worktree add failed ({base_commit[:8]}): {proc.stderr[:300]}")
    return worktree_path

def cleanup_worktree(bare_repo_path: Path, worktree_path: Path):
    """evaluationafter  worktree (force) ,  and fallbackdeletedirectory. """
    subprocess.run(
        ["git", "--git-dir", str(bare_repo_path), "worktree", "remove",
         "--force", str(worktree_path)],
        capture_output=True, text=True,
    )
    if worktree_path.exists():
        shutil.rmtree(worktree_path, ignore_errors=True)
                           
    subprocess.run(
        ["git", "--git-dir", str(bare_repo_path), "worktree", "prune"],
        capture_output=True, text=True,
    )

                                                         
                                         
                                                         
def _safe_resolve(repo_path: str, rel: str) -> Path:
    """for path resolve to  worktree in , then  (prevent path) . """
    root = Path(repo_path).resolve()
    target = (root / (rel or ".")).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"path (not at repoin ) : {rel}")
    return target

def execute_tool(tool_name: str, arguments: dict, repo_path: str) -> str:
    """at  worktree(repo_path) context in exec  linestool, returned textresults. """
    try:
        if tool_name == "find_files":
            pattern = arguments.get("pattern", "")
            if not pattern:
                return "ERROR: missing 'pattern'"
            root = Path(repo_path).resolve()
            matches = _glob.glob(str(root / pattern), recursive=True)
            rels = []
            for m in matches:
                p = Path(m).resolve()
                if p == root or root in p.parents:
                    rels.append(os.path.relpath(p, root))
            rels = sorted(rels)[:MAX_FIND_RESULTS]
            if not rels:
                return f"No files matching pattern: {pattern}"
            head = f"Found {len(rels)} file(s) (max {MAX_FIND_RESULTS}):\n"
            return head + "\n".join(rels)

        if tool_name == "read_file":
            path = arguments.get("path", "")
            if not path:
                return "ERROR: missing 'path'"
            target = _safe_resolve(repo_path, path)
            if not target.exists() or not target.is_file():
                return f"ERROR: file not found: {path}"
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            total = len(all_lines)
            start = arguments.get("start_line")
            end = arguments.get("end_line")
            start = int(start) if start else 1
            start = max(1, start)
            if end:
                end = int(end)
            else:
                end = start + MAX_READ_LINES - 1
            end = min(end, start + MAX_READ_LINES - 1, total)
            if start > total:
                return f"ERROR: start_line {start} exceeds file length {total}"
            chunk = all_lines[start - 1:end]
            numbered = "".join(f"{start + i}\t{ln.rstrip(chr(10))}\n"
                               for i, ln in enumerate(chunk))
            header = f"{path} (lines {start}-{end} of {total}):\n"
            return header + numbered

        if tool_name == "search_code":
            pattern = arguments.get("pattern", "")
            if not pattern:
                return "ERROR: missing 'pattern'"
            sub = arguments.get("path", "") or "."
            max_results = arguments.get("max_results")
            try:
                max_results = int(max_results) if max_results else MAX_SEARCH_RESULTS
            except (TypeError, ValueError):
                max_results = MAX_SEARCH_RESULTS
            max_results = max(1, min(max_results, MAX_SEARCH_RESULTS))
            search_root = _safe_resolve(repo_path, sub)
            if not search_root.exists():
                return f"ERROR: path not found: {sub}"
            proc = subprocess.run(
                ["grep", "-rnI", "-E", pattern, str(search_root)],
                capture_output=True, text=True, timeout=30,
            )
            root = Path(repo_path).resolve()
            out_lines = []
            for line in proc.stdout.splitlines():
                                             
                parts = line.split(":", 2)
                if len(parts) < 3:
                    continue
                abspath, lineno, content = parts
                try:
                    rel = os.path.relpath(Path(abspath).resolve(), root)
                except ValueError:
                    rel = abspath
                out_lines.append(f"{rel}:{lineno}: {content.strip()[:200]}")
                if len(out_lines) >= max_results:
                    break
            if not out_lines:
                return f"No matches for pattern: {pattern}"
            head = f"Found {len(out_lines)} match(es) (max {max_results}):\n"
            return head + "\n".join(out_lines)

        if tool_name == "list_dir":
            path = arguments.get("path", "") or "."
            target = _safe_resolve(repo_path, path)
            if not target.exists() or not target.is_dir():
                return f"ERROR: directory not found: {path}"
            entries = []
            for name in sorted(os.listdir(target)):
                full = target / name
                kind = "dir" if full.is_dir() else "file"
                entries.append(f"[{kind}] {name}")
            if not entries:
                return f"(empty directory: {path})"
            return f"{path} ({len(entries)} entries):\n" + "\n".join(entries)

        return f"ERROR: unknown tool '{tool_name}'"
    except Exception as e:                
        return f"ERROR: {type(e).__name__}: {str(e)[:200]}"

                                                         
                                                         
                                                         
async def call_llm_api_message(messages: list, api_key: str, tools: list = None,
                                 timeout: float = 300.0) -> dict:
    import httpx
    payload = {
        "model": MODEL_CONFIG["model_name"],
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 8192,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        return data["choices"][0]["message"]

async def call_with_retry(messages: list, api_key: str, tools: list,
                          max_retries: int = 3) -> dict:
    """with retry single  turnscall: coveragerate limit(429), timeout, emptyerror, connecterror. """
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                await asyncio.sleep(min(2 ** (attempt + 1), 30))
            return await call_llm_api_message(messages, api_key, tools)
        except Exception as e:                
            last_err = e
            continue
    raise last_err

def _clean_assistant_message(msg: dict) -> dict:
    """rebuild clean  assistant message (non-labelfield, keep tool_calls) . """
    out = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        out["tool_calls"] = msg["tool_calls"]
    return out

                                                         
                     
                                                         
async def generate_patch_agentic(case: dict, system_prompt: str, semaphore: asyncio.Semaphore,
                                 api_key: str, repo_dir: Path, worktrees_dir: Path,
                                 traces_dir: Path, index: int, total: int,
                                 max_turns: int) -> dict:
    async with semaphore:
        instance_id = case["instance_id"]
        repo = case.get("repo", "")
        base_commit = case.get("base_commit", "")
        user_prompt = USER_PROMPT_TEMPLATE.format(
            problem_statement=case.get("problem_statement", ""),
            hints_text=case.get("hints_text", "") or " (no ) ",
            repo=repo,
            version=case.get("version", ""),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        conversation = []                
        patch = ""
        final_content = ""
        n_tool_calls = 0
        turn = 0
        fail_reason = ""
        error = None
        worktree_path = worktrees_dir / instance_id
        t0 = time.time()

                                                                   
        repo_lock = await _get_repo_lock(repo)
        try:
            async with repo_lock:
                bare = await asyncio.to_thread(ensure_bare_repo, repo, repo_dir)
                await asyncio.to_thread(prepare_repo_worktree, bare, base_commit, worktree_path)
        except Exception as e:                
            error = f"{type(e).__name__}: {str(e)[:200]}"
            elapsed = time.time() - t0
            print(f"  [{index}/{total}] {instance_id}:  worktree prepare failed - {error}", flush=True)
            return _make_result(instance_id, "", elapsed, 0, 0, error,
                                case, traces_dir, system_prompt, user_prompt, [], "")

        try:
            for turn in range(1, max_turns + 1):
                use_tools = TOOLS if turn < max_turns else None
                if turn == max_turns:
                    messages.append({"role": "user", "content": FINAL_ROUND_PROMPT})
                elif turn > 1 and turn >= max_turns - 2:
                    messages.append({"role": "user",
                                     "content": NEAR_FINAL_PROMPT.format(remaining=max_turns - turn)})

                print(f"  [{index}/{total}] {instance_id} turn{turn}/{max_turns} "
                      f"LLMcalling(tools={'Y' if use_tools else 'N'})...", flush=True)
                msg = await call_with_retry(messages, api_key, use_tools)
                messages.append(_clean_assistant_message(msg))
                content = msg.get("content") or msg.get("reasoning_content") or ""
                if content:
                    final_content = content

                tool_calls = msg.get("tool_calls")
                if tool_calls and turn < max_turns:
                    for tc in tool_calls:
                        n_tool_calls += 1
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        try:
                            arguments = json.loads(fn.get("arguments") or "{}")
                        except json.JSONDecodeError:
                            arguments = {}
                        obs = await asyncio.to_thread(execute_tool, name, arguments,
                                                      str(worktree_path))
                        conversation.append({"turn": turn, "tool": name,
                                             "arguments": arguments, "obs": obs[:2000]})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "content": obs,
                        })
                    continue         

                                  
                patch = fix_hunk_counts(extract_patch(content))
                break
            else:
                fail_reason = f"out turnsbudget({max_turns})"

                                              
            if not patch and final_content:
                patch = fix_hunk_counts(extract_patch(final_content))

            elapsed = time.time() - t0
            icon = ""if patch else "⬜"
            print(f"  [{index}/{total}] {instance_id}: patch={'has ' if patch else 'empty'} {icon} "
                  f"(turns={turn} tools={n_tool_calls} {elapsed:.1f}s)", flush=True)
            return _make_result(instance_id, patch, elapsed, turn, n_tool_calls, None,
                                case, traces_dir, system_prompt, user_prompt,
                                conversation, final_content, fail_reason)

        except Exception as e:                
            error = f"{type(e).__name__}: {str(e)[:200]}"
                                  
            if not patch and final_content:
                patch = fix_hunk_counts(extract_patch(final_content))
            elapsed = time.time() - t0
            print(f"  [{index}/{total}] {instance_id}:  {error} "
                  f"(fallbackpatch={'has ' if patch else 'empty'})", flush=True)
            return _make_result(instance_id, patch, elapsed, turn, n_tool_calls, error,
                                case, traces_dir, system_prompt, user_prompt,
                                conversation, final_content)
        finally:
                                                
            try:
                async with repo_lock:
                    await asyncio.to_thread(cleanup_worktree, bare, worktree_path)
            except Exception:                
                pass

def _make_result(instance_id: str, patch: str, elapsed: float, turns: int,
                 n_tool_calls: int, error, case: dict, traces_dir: Path,
                 system_prompt: str, user_prompt: str, conversation: list,
                 final_content: str, fail_reason: str = "") -> dict:
    """ trace file + returned  and  test_swebench for aligned  prediction record. """
    trace = {
        "instance_id": instance_id,
        "repo": case.get("repo", ""),
        "version": case.get("version", ""),
        "base_commit": case.get("base_commit", ""),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "conversation": conversation,
        "final_content": final_content,
        "patch": patch,
        "n_turns": turns,
        "n_tool_calls": n_tool_calls,
        "elapsed_seconds": round(elapsed, 2),
        "fail_reason": fail_reason,
        "error": error,
        "eval_result": None,
        "timestamp": datetime.now().isoformat(),
    }
    (traces_dir / f"trace_{instance_id}.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "instance_id": instance_id,
        "model_name_or_path": MODEL_CONFIG["model_name"],
        "model_patch": patch,
        "_elapsed": round(elapsed, 2),
        "_turns": turns,
        "_tool_calls": n_tool_calls,
        "_empty": not bool(patch),
        "_error": error,
    }

                                                         
     
                                                         
async def run(args):
    print("=" * 70)
    print("SWE-bench multi- turns Agent evaluation Harness")
    print("=" * 70)

    MODEL_CONFIG["model_name"] = provider_model(MODEL_CONFIG["model_name"])
    api_key = openai_compatible_api_key(MODEL_CONFIG["api_key_env"])
    print(f"\n model: {openai_compatible_provider_label()} / {MODEL_CONFIG['model_name']}")

    skill_content = load_skill(Path(args.skill))
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(skill_content=skill_content)
    print(f"Skill: {args.skill}")

    cases = load_dataset(Path(args.dataset))
    if args.filter_ids:
        cases = [c for c in cases if c["instance_id"] in args.filter_ids]
    if args.limit > 0:
        cases = cases[:args.limit]
    print(f"data: {len(cases)} instances from {args.dataset}")
    if not cases:
        print("no evaluable instances")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    traces_dir = output_dir / "traces"
    output_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    predictions_file = output_dir / "predictions.jsonl"

    repo_dir = Path(args.repo_dir)
    if not repo_dir.is_absolute():
        repo_dir = PROJECT_ROOT / repo_dir
    repo_dir.mkdir(parents=True, exist_ok=True)
    worktrees_dir = output_dir / "_worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)

    print(f"output directory: {output_dir}")
    print(f"bare repo directory: {repo_dir}")
    print(f"concurrency: {args.concurrency}  |  max turns: {args.max_turns}  |  evaluation workers: {args.max_workers}")

                                                  
    existing = load_existing_predictions(predictions_file)
    pending = [c for c in cases if c["instance_id"] not in existing]
    if existing:
        print(f"resume from checkpoint: existing {len(existing)}  items predictions, pending generation {len(pending)}  items")

                                                       
    concurrency = max(1, min(args.concurrency, 20))
    semaphore = asyncio.Semaphore(concurrency)
    start = time.time()
    new_preds = {}
    if pending:
        tasks = [
            generate_patch_agentic(c, system_prompt, semaphore, api_key, repo_dir,
                                   worktrees_dir, traces_dir, i + 1, len(pending),
                                   args.max_turns)
            for i, c in enumerate(pending)
        ]
        gen_results = await asyncio.gather(*tasks)
        new_preds = {r["instance_id"]: r for r in gen_results}
    elapsed = time.time() - start
    print(f"\n  generation time: {elapsed:.1f}s")

                
    all_preds = dict(existing)
    all_preds.update(new_preds)

                                   
    with open(predictions_file, "w", encoding="utf-8") as f:
        for c in cases:
            iid = c["instance_id"]
            p = all_preds.get(iid, {})
            f.write(json.dumps({
                "instance_id": iid,
                "model_name_or_path": MODEL_CONFIG["model_name"],
                "model_patch": p.get("model_patch", ""),
            }, ensure_ascii=False) + "\n")
    empty_n = sum(1 for c in cases if not all_preds.get(c["instance_id"], {}).get("model_patch"))
    print(f"predictions: {predictions_file}  (empty patch {empty_n}/{len(cases)})")

                       
    shutil.rmtree(worktrees_dir, ignore_errors=True)

    if args.skip_eval:
        print("\n  --skip_eval already set, skipping Docker evaluation, only produces predictions. ")
        print("=" * 70)
        return

                                                       
    report_file = run_swebench_eval(predictions_file, Path(args.dataset),
                                    args.run_id, args.max_workers)
    final_report = {}
    if report_file.exists():
        try:
            final_report = json.loads(report_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"failed to parse the final report: {report_file}")
    else:
        print(f"final report file not found: {report_file}")

    instance_ids = [c["instance_id"] for c in cases]
    per_instance = parse_per_instance_status(args.run_id, instance_ids)

                            
    resolved_ids = set(final_report.get("resolved_ids", []))
    for iid in instance_ids:
        tf = traces_dir / f"trace_{iid}.json"
        if tf.exists():
            try:
                tr = json.loads(tf.read_text(encoding="utf-8"))
                tr["eval_result"] = {
                    "resolved": iid in resolved_ids,
                    "tests_status": per_instance.get(iid, {}).get("tests_status"),
                }
                tf.write_text(json.dumps(tr, ensure_ascii=False, indent=2), encoding="utf-8")
            except json.JSONDecodeError:
                pass

                                                        
    results, report = build_results(cases, all_preds, final_report, per_instance)
    report["run_id"] = args.run_id
    report["mode"] = "agentic_multiturn"
    report["max_turns"] = args.max_turns
    report["skill_path"] = str(args.skill)
    report["dataset_path"] = str(args.dataset)
    report["gen_elapsed_seconds"] = round(elapsed, 1)
    report["avg_turns"] = round(
        sum(p.get("_turns", 0) for p in new_preds.values()) / len(new_preds), 2
    ) if new_preds else 0
    report["avg_tool_calls"] = round(
        sum(p.get("_tool_calls", 0) for p in new_preds.values()) / len(new_preds), 2
    ) if new_preds else 0

    results_file = output_dir / "results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    report_out = output_dir / "report.json"
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*70}")
    print("evaluation results")
    print(f"{'='*70}")
    print(f"  total instances: {report['total']}")
    print(f"  Resolved: {report['resolved']}  Failed: {report['failed']}  Error: {report['error']}")
    print(f"  Resolved Rate: {report['resolved_rate']}%")
    print(f"  avg turns: {report['avg_turns']}  avg tool calls: {report['avg_tool_calls']}")
    print("  by repository:")
    for repo, v in report["per_repo_accuracy"].items():
        print(f"    {repo}: {v['resolved']}/{v['total']} ({v['rate']}%)")
    print(f"\n report: {report_out}")
    print(f"per-instance results: {results_file}")
    print(f"traces: {traces_dir}")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="SWE-bench multi- turns Agent evaluation Harness")
    parser.add_argument("--skill", required=True, help="SKILL.md filepath ( or at directory) ")
    parser.add_argument("--dataset", required=True, help="datasetpath (.jsonl) ")
    parser.add_argument("--repo_dir", default="data/swebench/repos",
                        help="local  bare repo store directory (default data/swebench/repos) ")
    parser.add_argument("--max_turns", type=int, default=10, help="max interaction turns (default 10) ")
    parser.add_argument("--concurrency", type=int, default=6, help="concurrencygenerate  (default 6, cap 20) ")
    parser.add_argument("--max_workers", type=int, default=4, help="SWE-bench evaluationparallel worker  count")
    parser.add_argument("--run_id", default="agentic", help=" timesevaluation run_id (SWE-bench harness use ) ")
    parser.add_argument("--output_dir", required=True, help="resultsoutput directory")
    parser.add_argument("--skip_eval", action="store_true", help="only generate  predictions, not run  Docker evaluation")
    parser.add_argument("--limit", type=int, default=0, help="only run top  N  items (0=full ) ")
    parser.add_argument("--filter-ids", nargs="*", default=[], dest="filter_ids",
                        help="only evaluationspecified  instance_id")
    args = parser.parse_args()

    if not Path(args.dataset).is_absolute():
        args.dataset = str(PROJECT_ROOT / args.dataset)
    if not Path(args.skill).is_absolute():
        args.skill = str(PROJECT_ROOT / args.skill)
    if not Path(args.dataset).exists():
        print(f"dataset not found: {args.dataset}")
        sys.exit(1)

    asyncio.run(run(args))

if __name__ == "__main__":
    main()
