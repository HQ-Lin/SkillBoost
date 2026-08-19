#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

                                                        
sys.path.insert(0, str(Path(__file__).parent))
from test_officeqa import (              
    exact_match, sub_em, token_f1, num_em,
    parse_answer, parse_reason,
)

                                                    
SOURCE_OFFICEQA = Path("/path/to/source_env/officeqa")
sys.path.insert(0, str(SOURCE_OFFICEQA))
from tool_runtime import resolve_docs_roots, resolve_candidate_files              

                                                         
                                           
                                                         

MODEL_NAME = "claude-opus-4-7"
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
ALLOWED_TOOLS = ["Read", "Grep", "Glob"]

                                                         
                                        
                                                         

PROMPT_TEMPLATE = """\
you  is one namedocument countvalue QAexpert. use you with  Read / Grep / Glob tool, **only at columnspecified docsin **retrievalevidence, then based on at evidence extraction/compute the answer.

【retrievalscope (strictrestricted ) 】only for with fileuse  Read/Grep (when top directory, use give  filenamecan ) :
{file_block}
forbiddenread or retrievalsingle  any file.

【docstrait】single  docscan  count100kchars, no cannot read the whole document. must follow"locate first, then read closely" retrievalworkflow:
1. use  Grep searchquestions in  key entity (organizationname, countryname, tablelabel questions, year-month, feature count) locate lines；
2. use  Read readhit linesnearby window, view full  table lines and columnwith ；
3. if questions and multi-  countvalue/multi- pages/multi- quarter, repeat Grep+Read cross locateper one  countvalue；
4. read the column header carefully questions and single  (thousand USD/million USD/percentage) , confirm linescolumnfor align before extracting count；
5. by questionsrequire requires addition or subtraction/compare/difference etccompute.

【answer format rules】
{skill_content}

{question}

{hint_block}

【outputrequire 】retrievalto sufficientevidenceafter , at  **the last  lines**only outputone  JSON for  (not require  markdown guardrail) :
{{"answer": "final  countvalue or columntable", "reason": "one-sentence evidence/computenote (≤120 ) "}}
even if partial datamissing, also require use retrievalto  datagive the most has confidence  countvalue/columntableestimate；only has donefull no retrievalto any related countvalue, then output {{"answer": "NOT_FOUND", "reason": "missingnote"}}. """

                                                         
                  
                                                         

async def call_claude_cli(prompt: str, cwd: str, max_turns: int,
                          timeout: float = 420.0) -> dict:
    """passed claude -p call claude-opus-4-7, returned parseafter  result JSON.

    returned field (claude --output-format json) : result/num_turns/total_cost_usd/
    is_error/subtype/session_id  etc.
    """
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--model", MODEL_NAME,
        "--max-turns", str(max_turns),
        "--output-format", "json",
        "--allowedTools", *ALLOWED_TOOLS,
        "--disallowedTools", "Bash", "Write", "Edit", "WebFetch", "WebSearch",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ.copy(),
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"claude CLI timeout (>{timeout}s) ")
    out = stdout.decode("utf-8", "replace").strip()
    err = stderr.decode("utf-8", "replace").strip()
    if not out:
        raise RuntimeError(f"claude CLI no output | stderr: {err[:300]}")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
                           
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        else:
            raise RuntimeError(f"claude CLI outputnon- JSON: {out[:300]}")
    if data.get("is_error"):
        raise RuntimeError(f"claude CLI : {data.get('subtype')} | {str(data.get('result'))[:200]}")
    return data

async def call_with_retry(prompt: str, cwd: str, max_turns: int,
                          max_retries: int = 2) -> dict:
    """with retry, coveragerate limit(429) and timeout. """
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                await asyncio.sleep(min(5 * (2 ** attempt), 30))
            return await call_claude_cli(prompt, cwd, max_turns)
        except Exception as e:                
            last_err = e
            continue
    raise last_err

                                                         
           
                                                         

async def run_case(case: dict, skill_content: str, semaphore: asyncio.Semaphore,
                   docs_roots: list, docs_cwd: str, traces_dir: Path,
                   index: int, total: int, max_turns: int) -> dict:
    async with semaphore:
        task_id = case["task_id"]
        gold = str(case["gold_answer"])

        candidate_files = resolve_candidate_files(case.get("source_files", []), docs_roots)
        allowed_names = [os.path.basename(p) for p in candidate_files]
        file_block = "\n".join(f"- {n}" for n in allowed_names) or "-  (not parseto file) "
        hint_block = "\n".join(f"- {h}" for h in case.get("source_docs", [])) or "-  (no ) "
        prompt = PROMPT_TEMPLATE.format(
            file_block=file_block, hint_block=hint_block,
            skill_content=skill_content, question=case["question"],
        )

        pred = reason = ""
        result_text = ""
        n_turns = 0
        cost = 0.0
        fail_reason = ""
        try:
            data = await call_with_retry(prompt, docs_cwd, max_turns)
            result_text = data.get("result") or ""
            n_turns = int(data.get("num_turns") or 0)
            cost = float(data.get("total_cost_usd") or 0.0)
            pred = parse_answer(result_text)
            reason = parse_reason(result_text)

            em = exact_match(pred, gold)
            f1 = token_f1(pred, gold)
            sem_ = sub_em(pred, gold)
            nem = num_em(pred, gold)
            correct = (em == 1.0) or (nem == 1.0)

            icon = ""if correct else ""
            print(f"  [{index}/{total}] {task_id}: pred='{pred[:32]}' gold='{gold[:32]}' "
                  f"turns={n_turns} ${cost:.3f} {icon}")

            trace = {
                "task_id": task_id, "question": case["question"], "gold": gold,
                "predicted": pred, "em": em, "f1": f1, "sub_em": sem_, "num_em": nem,
                "correct": correct, "reason": reason,
                "n_turns": n_turns, "cost_usd": cost,
                "candidate_files": candidate_files,
                "result_text": result_text, "fail_reason": fail_reason,
                "timestamp": datetime.now().isoformat(),
            }
            with open(traces_dir / f"trace_{task_id}.json", "w", encoding="utf-8") as f:
                json.dump(trace, f, ensure_ascii=False, indent=2)

            return {
                "task_id": task_id, "question": case["question"], "gold": gold,
                "predicted": pred, "em": em, "f1": f1, "sub_em": sem_, "num_em": nem,
                "correct": correct, "reason": reason,
                "n_turns": n_turns, "cost_usd": cost,
                "difficulty": case.get("difficulty", ""),
                "trace_file": str(traces_dir / f"trace_{task_id}.json"),
            }
        except Exception as e:                
            print(f"  [{index}/{total}] {task_id}:  ERROR {e}")
            return {
                "task_id": task_id, "question": case["question"], "gold": gold,
                "predicted": "", "em": 0.0, "f1": 0.0, "sub_em": 0.0, "num_em": 0.0,
                "correct": False, "reason": "", "error": str(e),
                "n_turns": n_turns, "cost_usd": cost,
                "difficulty": case.get("difficulty", ""), "trace_file": None,
            }

                                                         
     
                                                         

async def run_evaluation(args):
    print("=" * 70)
    print("OfficeQA multi- turnsretrievalevaluation —— claude-opus-4-7 (Claude Code CLI, plan A)")
    print("=" * 70)

    if not os.environ.get("ANTHROPIC_AUTH_TOKEN") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("not set ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY")
        sys.exit(1)
    print(f"\n model: {MODEL_NAME} via {CLAUDE_BIN} -p")

    docs_roots = resolve_docs_roots()
    docs_cwd = docs_roots[0]
    print(f"docs root(cwd): {docs_cwd}")

    skill_path = Path(args.skill)
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        print(f"Skill file not found: {skill_file}")
        sys.exit(1)
    skill_content = skill_file.read_text(encoding="utf-8")
    if skill_content.startswith("---"):
        end_idx = skill_content.find("---", 3)
        if end_idx != -1:
            skill_content = skill_content[end_idx + 3:].strip()
    print(f"Skill: {skill_path}")

    jsonl_path = Path(args.data)
    test_cases = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                test_cases.append(json.loads(line))
    if args.filter_ids:
        test_cases = [c for c in test_cases if c["task_id"] in args.filter_ids]
        print(f"   after filtering {len(test_cases)} cases")
    if args.limit > 0:
        test_cases = test_cases[:args.limit]
        print(f"    truncated to first  {len(test_cases)} cases")
    print(f"data: {len(test_cases)} cases from {jsonl_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output_base) if args.output_base else Path(__file__).parent.parent / "evolved" / "officeqa-solver"
    if not output_base.is_absolute():
        output_base = Path(__file__).parent.parent / output_base
    dataset_name = Path(args.data).stem
    run_dir = output_base / f"{dataset_name}_claude_run_{timestamp}"
    evals_dir = run_dir / "evals"
    traces_dir = run_dir / "traces"
    evals_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    print(f"output: {run_dir}")
    print(f"concurrency: {args.max_concurrent}  max turns: {args.max_turns}")

    semaphore = asyncio.Semaphore(args.max_concurrent)
    start = time.time()
    tasks = [
        run_case(c, skill_content, semaphore, docs_roots, docs_cwd,
                 traces_dir, i + 1, len(test_cases), args.max_turns)
        for i, c in enumerate(test_cases)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    print(f"\n  elapsed: {elapsed:.1f}s")

    total = len(results)
    err = sum(1 for r in results if r.get("error"))
    nf = sum(1 for r in results if str(r.get("predicted", "")).upper().startswith("NOT_FOUND"))
    empty = sum(1 for r in results if not str(r.get("predicted", "")).strip())
    em_mean = sum(r["em"] for r in results) / total * 100 if total else 0
    f1_mean = sum(r["f1"] for r in results) / total * 100 if total else 0
    sub_em_mean = sum(r["sub_em"] for r in results) / total * 100 if total else 0
    num_em_mean = sum(r["num_em"] for r in results) / total * 100 if total else 0
    correct = sum(1 for r in results if r["correct"])
    acc = correct / total * 100 if total else 0
    avg_turns = sum(r.get("n_turns", 0) for r in results) / total if total else 0
    total_cost = sum(r.get("cost_usd", 0.0) for r in results)

    print(f"\n{'='*70}")
    print(f"evaluation results")
    print(f"{'='*70}")
    print(f"  total case: {total}, execution exception: {err}, NOT_FOUND: {nf}, emptypredicted : {empty}")
    print(f"  Accuracy (EM ∨ NumEM): {acc:.2f}% ({correct}/{total})")
    print(f"  EM: {em_mean:.2f}%  F1: {f1_mean:.2f}%  Sub-EM: {sub_em_mean:.2f}%  Num-EM: {num_em_mean:.2f}%")
    print(f"avg turns: {avg_turns:.1f}  totalcost: ${total_cost:.2f}  (avg  ${total_cost/total if total else 0:.3f}/case)")

    diffs = sorted(set(r.get("difficulty", "") for r in results))
    for d in diffs:
        if not d:
            continue
        sub = [r for r in results if r.get("difficulty") == d]
        sub_acc = sum(1 for r in sub if r["correct"]) / len(sub) * 100
        print(f"  [{d}] n={len(sub)} Acc={sub_acc:.2f}%")

    wrong = [r for r in results if not r["correct"]]
    if wrong:
        print(f"\n failed case ({len(wrong)}  total, showing first  20):")
        for w in wrong[:20]:
            print(f"  {w['task_id']}: gold='{w['gold'][:30]}' pred='{w['predicted'][:30]}' | {w.get('reason','')[:60]}")

    result_file = evals_dir / f"results_{dataset_name}_{timestamp}.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "run_timestamp": timestamp,
        "mode": "agentic_claude_cli_scheme1",
        "model": MODEL_NAME,
        "base_url": os.environ.get("ANTHROPIC_BASE_URL", ""),
        "skill_path": str(skill_path),
        "data_path": str(jsonl_path),
        "max_turns": args.max_turns,
        "max_concurrent": args.max_concurrent,
        "total": total, "correct": correct, "error_count": err,
        "not_found_count": nf, "empty_count": empty,
        "fail_ids": [r["task_id"] for r in results if not r["correct"]],
        "accuracy": round(acc, 2), "em": round(em_mean, 2), "f1": round(f1_mean, 2),
        "sub_em": round(sub_em_mean, 2), "num_em": round(num_em_mean, 2),
        "avg_turns": round(avg_turns, 2),
        "total_cost_usd": round(total_cost, 4),
        "elapsed_seconds": round(elapsed, 1),
        "results_file": str(result_file),
        "traces_dir": str(traces_dir), "run_dir": str(run_dir),
    }
    summary_file = evals_dir / f"report_{dataset_name}_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n results: {result_file}")
    print(f"report: {summary_file}")
    print(f"run directory: {run_dir}")
    print("=" * 70)
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OfficeQA evaluation (claude-opus-4-7 via Claude Code CLI) ")
    parser.add_argument("--data", "-d", required=True)
    parser.add_argument("--skill", "-s", required=True)
    parser.add_argument("--filter-ids", "-f", nargs="*", default=[], dest="filter_ids")
    parser.add_argument("--limit", "-l", type=int, default=0)
    parser.add_argument("--max-concurrent", "-c", type=int, default=8, dest="max_concurrent")
    parser.add_argument("--max-turns", "-t", type=int, default=20, dest="max_turns")
    parser.add_argument("--output-base", "-o", default="", dest="output_base")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    if not Path(args.data).is_absolute():
        args.data = str(project_root / args.data)
    if not Path(args.skill).is_absolute():
        args.skill = str(project_root / args.skill)
    if not Path(args.data).exists():
        print(f"dataset not found: {args.data}")
        sys.exit(1)
    if not Path(args.skill).exists():
        print(f"Skill directory not found: {args.skill}")
        sys.exit(1)

    asyncio.run(run_evaluation(args))
