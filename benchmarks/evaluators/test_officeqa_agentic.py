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
    normalize_answer, exact_match, sub_em, token_f1, num_em,
    parse_answer, parse_reason,
)
from provider import (
    async_chat_completion,
    openai_compatible_api_key,
    openai_compatible_provider_label,
    provider_model,
)

                                                               
SOURCE_OFFICEQA = Path("/path/to/source_env/officeqa")
sys.path.insert(0, str(SOURCE_OFFICEQA))
import tool_runtime              
from tool_runtime import run_tool, resolve_docs_roots, resolve_candidate_files              

                                                         
      
                                                         

MODEL_CONFIG_GENERIC = {
    "model_provider": "openai-compatible",
    "model_name": "qwen3.6-plus",
    "api_key_env": "LLM_API_KEY",
    "base_url": None,
}

ACTIVE_MODEL_CONFIG = MODEL_CONFIG_GENERIC

                                                         
                                  
                                                         

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Find candidate local document files by filename or relative-path glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read a local text document excerpt by absolute path and line window (start line, limit lines). Returns at most ~4000 chars.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search a local text document for a literal (case-insensitive) pattern and return matching lines as 'lineno: content'. Returns at most 20 matches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern", "path"],
            },
        },
    },
]

                                                         
        
                                                         

SYSTEM_PROMPT_TEMPLATE = """\
you  is one namedocument countvalue QAexpert. you can with calltool, at official documentdocs (Treasury Bulletin / Federal Reserve Bulletin  etcpure text)  in retrievalevidence, then based on at evidence extraction/compute the answer.

【can use tool】
- grep(pattern, path): at specified docs in by charsstring (not large ) search, returned match lines (format " lines: content") , at most  20  lines. use at locatekey entity/ /tablename/ countat position.
- read(path, start, limit): readdocsspecified  lineswindow (from # start  lines limit  lines) , at most returned  4000 chars. use at viewhit linesnearby fulltablecontext.
- glob(pattern): by filenamemodecolumnout candidatedocs (one no requires use , fileat use  in give ) .

【docstrait】single  docscan  count100kchars, no cannot read the whole document. must follow"locate first, then read closely" retrievalworkflow:
1. use  grep searchquestions in  key entity (organizationname, countryname, tablelabel questions, year-month, feature count) locate lines；
2. use  read readhit linesnearby window (like  start=hit lines-5, limit=40) , view full  table lines and columnwith ；
3. if questions and multi-  countvalue/multi- pages/multi- quarter, repeat grep+read cross locateper one  countvalue；
4. read the column header carefully questions and single  (thousand USD/million USD/percentage) , confirm linescolumnfor align before extracting count；
5. by questionsrequire requires addition or subtraction/compare/difference etccompute.

【answer format rules】
{skill_content}

【outputrequire 】when  and only when you retrievalto sufficientevidence, not then need calltool, outputfinal answer. final answeronly output JSON (not require any  markdown wrap, not require multi-extra text) :
{{"answer": "final  countvalue or columntable", "reason": "one-sentence evidence/computenote (≤120 ) "}}
if retrievalfind not to evidence, output {{"answer": "NOT_FOUND", "reason": ""}}. """

USER_PROMPT_TEMPLATE = """\
{question}

{file_block}

{hint_block}

first use toolretrievalevidence, then give final  JSON answer. """

                                                   
NEAR_FINAL_PROMPT = """\
prompt: you have  {remaining}  turnstool callschances left. plan them well, requires evidencecheck for after then ；not must  as turns rate. """

FINAL_ROUND_PROMPT = """\
 this  is the last  turns, tool disableduse , you no then retrieval. you mustbase at retrievalto  evidenceoutputfinal  JSON answer: {"answer": "...", "reason": "..."}.
**even if partial datamissing, also require use retrievalto  datagive the most has confidence  countvalue/columntableestimate** (examplelike use existing countcompute, use , use grasp trend) , not can outputemptycontent, not can request againretrieval.
only has when you **donefull no retrievalto any related countvalue**, then output {"answer": "NOT_FOUND", "reason": "missingnote"}. only outputpure  JSON, not require  markdown guardrail, not require multi-extra text. """

                                                         
                                       
                                                         

async def call_llm_api_message(messages: list, model_name: str, api_key: str,
                                 tools: list = None, timeout: float = 600.0) -> dict:
    import httpx
    payload = {"model": model_name, "messages": messages, "temperature": 0.1, "max_tokens": 16384}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        return data["choices"][0]["message"]

async def call_with_retry(messages: list, model_config: dict, tools: list,
                          max_retries: int = 3) -> dict:
    """with retry single  turnscall. coveragerate limit(429) and networkerror(DNS/timeout). """
    api_key = openai_compatible_api_key(model_config["api_key_env"])
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                await asyncio.sleep(min(2 ** attempt, 15))
            return await call_llm_api_message(messages, model_config["model_name"], api_key, tools)
        except Exception as e:                
            last_err = e
            continue
    raise last_err

                                                         
        
                                                         

def _clean_assistant_message(msg: dict) -> dict:
    """rebuild clean  assistant message ( reasoning_content  etcnon-labelfield, keep tool_calls) . """
    out = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        out["tool_calls"] = msg["tool_calls"]
    return out

async def run_agentic_case(case: dict, system_prompt: str, semaphore: asyncio.Semaphore,
                           model_config: dict, docs_roots: list, traces_dir: Path,
                           index: int, total: int, max_turns: int) -> dict:
    async with semaphore:
        task_id = case["task_id"]
        gold = str(case["gold_answer"])

                                                     
        candidate_files = resolve_candidate_files(case.get("source_files", []), docs_roots)
        allowed_files = [os.path.basename(p) for p in candidate_files]

        file_block = "\n".join(f"- {p}" for p in candidate_files) or "-  (not parseto file) "
        hint_block = "\n".join(f"- {h}" for h in case.get("source_docs", [])) or "-  (no ) "
        user_prompt = USER_PROMPT_TEMPLATE.format(
            question=case["question"], file_block=file_block, hint_block=hint_block,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        conversation = []                 
        pred = ""
        reason = ""
        final_content = ""
        n_tool_calls = 0
        fail_reason = ""

        try:
            for turn in range(1, max_turns + 1):
                                       
                use_tools = TOOL_SCHEMAS if turn < max_turns else None
                                                            
                if turn == max_turns:
                    messages.append({"role": "user", "content": FINAL_ROUND_PROMPT})
                elif turn > 1 and turn >= max_turns - 2:
                    messages.append({"role": "user",
                                     "content": NEAR_FINAL_PROMPT.format(remaining=max_turns - turn)})
                import time as _time
                _t0 = _time.time()
                print(f"  [{index}/{total}] {task_id} turn{turn}/{max_turns} LLMcalling(tools={'Y' if use_tools else 'N'})...", flush=True)
                msg = await call_with_retry(messages, model_config, use_tools)
                print(f"  [{index}/{total}] {task_id} turn{turn} LLMreturned  elapsed{_time.time()-_t0:.0f}s "
                      f"content={len(msg.get('content') or '')} tool_calls={len(msg.get('tool_calls') or [])}", flush=True)
                messages.append(_clean_assistant_message(msg))
                                                                       
                content = msg.get("content") or msg.get("reasoning_content") or ""
                final_content = content or final_content

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
                        cmd, obs = run_tool(name, arguments,
                                            allowed_roots=docs_roots, allowed_files=allowed_files)
                        conversation.append({"turn": turn, "cmd": cmd, "obs": obs[:2000]})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "content": obs,
                        })
                    continue         

                                
                pred = parse_answer(content)
                reason = parse_reason(content)
                break
            else:
                fail_reason = f"out retrievalturnsbudget({max_turns})"

            if not pred and final_content:
                pred = parse_answer(final_content)
                reason = reason or parse_reason(final_content)

            em = exact_match(pred, gold)
            f1 = token_f1(pred, gold)
            sem_ = sub_em(pred, gold)
            nem = num_em(pred, gold)
            correct = (em == 1.0) or (nem == 1.0)

            icon = ""if correct else ""
            print(f"  [{index}/{total}] {task_id}: pred='{pred[:36]}' gold='{gold[:36]}' "
                  f"turns={turn} tools={n_tool_calls} EM={em:.0f} {icon}")

            trace = {
                "task_id": task_id,
                "question": case["question"],
                "gold": gold,
                "predicted": pred,
                "em": em, "f1": f1, "sub_em": sem_, "num_em": nem,
                "correct": correct,
                "reason": reason,
                "n_turns": turn,
                "n_tool_calls": n_tool_calls,
                "candidate_files": candidate_files,
                "conversation": conversation,
                "final_content": final_content,
                "fail_reason": fail_reason,
                "timestamp": datetime.now().isoformat(),
            }
            trace_file = traces_dir / f"trace_{task_id}.json"
            with open(trace_file, "w", encoding="utf-8") as f:
                json.dump(trace, f, ensure_ascii=False, indent=2)

            return {
                "task_id": task_id,
                "question": case["question"],
                "gold": gold,
                "predicted": pred,
                "em": em, "f1": f1, "sub_em": sem_, "num_em": nem,
                "correct": correct,
                "reason": reason,
                "n_turns": turn,
                "n_tool_calls": n_tool_calls,
                "difficulty": case.get("difficulty", ""),
                "trace_file": str(trace_file),
            }

        except Exception as e:                
            err_str = f"{type(e).__name__}: {str(e)[:200]}"
                                                       
            if not pred and final_content:
                pred = parse_answer(final_content)
                reason = reason or parse_reason(final_content)
            em = exact_match(pred, gold) if pred else 0.0
            f1 = token_f1(pred, gold) if pred else 0.0
            sem_ = sub_em(pred, gold) if pred else 0.0
            nem = num_em(pred, gold) if pred else 0.0
            correct = (em == 1.0) or (nem == 1.0)
            print(f"  [{index}/{total}] {task_id}:  {err_str} (fallbackpred='{pred[:30]}')")
            return {
                "task_id": task_id,
                "question": case["question"],
                "gold": gold,
                "predicted": pred,
                "em": em, "f1": f1, "sub_em": sem_, "num_em": nem,
                "correct": correct,
                "reason": reason,
                "error": err_str,
                "n_turns": 0,
                "n_tool_calls": n_tool_calls,
                "difficulty": case.get("difficulty", ""),
                "trace_file": None,
            }

                                                         
     
                                                         

async def run_evaluation(args):
    print("=" * 70)
    print("OfficeQA multi- turnsretrievalevaluation (plan A: restricted  gold file half oracle Agent) ")
    print("=" * 70)

    model_config = dict(ACTIVE_MODEL_CONFIG)
    model_config["model_provider"] = openai_compatible_provider_label()
    model_config["model_name"] = provider_model(model_config["model_name"])
    if getattr(args, "model", ""):
        model_config["model_name"] = args.model
    print(f"\n model: {model_config['model_provider']} / {model_config['model_name']}")

             
    docs_roots = resolve_docs_roots()
    print(f"docs root: {docs_roots}")

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
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(skill_content=skill_content)
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
    run_dir = output_base / f"{dataset_name}_agentic_run_{timestamp}"
    evals_dir = run_dir / "evals"
    traces_dir = run_dir / "traces"
    evals_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    print(f"output: {run_dir}")
    print(f"concurrency: {args.max_concurrent}  max retrieval turns times: {args.max_turns}")

    semaphore = asyncio.Semaphore(args.max_concurrent)
    start = time.time()
    tasks = [
        run_agentic_case(c, system_prompt, semaphore, model_config, docs_roots,
                         traces_dir, i + 1, len(test_cases), args.max_turns)
        for i, c in enumerate(test_cases)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    print(f"\n  elapsed: {elapsed:.1f}s")

        
    total = len(results)
    err = sum(1 for r in results if r.get("error"))
    nf = sum(1 for r in results if str(r.get("predicted", "")).upper().startswith("NOT_FOUND"))
    em_mean = sum(r["em"] for r in results) / total * 100 if total else 0
    f1_mean = sum(r["f1"] for r in results) / total * 100 if total else 0
    sub_em_mean = sum(r["sub_em"] for r in results) / total * 100 if total else 0
    num_em_mean = sum(r["num_em"] for r in results) / total * 100 if total else 0
    correct = sum(1 for r in results if r["correct"])
    acc = correct / total * 100 if total else 0
    avg_turns = sum(r.get("n_turns", 0) for r in results) / total if total else 0
    avg_tools = sum(r.get("n_tool_calls", 0) for r in results) / total if total else 0

    print(f"\n{'='*70}")
    print(f"evaluation results")
    print(f"{'='*70}")
    print(f"  total case: {total}, execution exception: {err}, NOT_FOUND: {nf}")
    print(f"  Accuracy (EM ∨ NumEM): {acc:.2f}% ({correct}/{total})")
    print(f"  EM:     {em_mean:.2f}%")
    print(f"  F1:     {f1_mean:.2f}%")
    print(f"  Sub-EM: {sub_em_mean:.2f}%")
    print(f"  Num-EM: {num_em_mean:.2f}%")
    print(f"  avgretrieval turns times: {avg_turns:.1f}, avg tool calls: {avg_tools:.1f}")

    diffs = sorted(set(r.get("difficulty", "") for r in results))
    for d in diffs:
        if not d:
            continue
        sub = [r for r in results if r.get("difficulty") == d]
        if not sub:
            continue
        sub_acc = sum(1 for r in sub if r["correct"]) / len(sub) * 100
        sub_em_local = sum(r["em"] for r in sub) / len(sub) * 100
        print(f"  [{d}] n={len(sub)} Acc={sub_acc:.2f}% EM={sub_em_local:.2f}%")

    wrong = [r for r in results if not r["correct"]]
    if wrong:
        print(f"\n failed case ({len(wrong)}  total, showing first  20):")
        for w in wrong[:20]:
            print(f"  {w['task_id']}: gold='{w['gold'][:36]}' pred='{w['predicted'][:36]}' | {w.get('reason','')[:70]}")

    result_file = evals_dir / f"results_{dataset_name}_{timestamp}.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "run_timestamp": timestamp,
        "mode": "agentic_multiturn_scheme1",
        "model": f"{model_config['model_provider']}/{model_config['model_name']}",
        "skill_path": str(skill_path),
        "data_path": str(jsonl_path),
        "max_turns": args.max_turns,
        "max_concurrent": args.max_concurrent,
        "total": total,
        "correct": correct,
        "error_count": err,
        "not_found_count": nf,
        "fail_ids": [r["task_id"] for r in results if not r["correct"]],
        "accuracy": round(acc, 2),
        "em": round(em_mean, 2),
        "f1": round(f1_mean, 2),
        "sub_em": round(sub_em_mean, 2),
        "num_em": round(num_em_mean, 2),
        "avg_turns": round(avg_turns, 2),
        "avg_tool_calls": round(avg_tools, 2),
        "elapsed_seconds": round(elapsed, 1),
        "results_file": str(result_file),
        "traces_dir": str(traces_dir),
        "run_dir": str(run_dir),
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
    parser = argparse.ArgumentParser(description="OfficeQA multi- turnsretrievalevaluation (plan A) ")
    parser.add_argument("--data", "-d", required=True, help="datasetpath (_agentic.jsonl) ")
    parser.add_argument("--skill", "-s", required=True, help="Skill directorypath")
    parser.add_argument("--filter-ids", "-f", nargs="*", default=[], dest="filter_ids", help="only evaluationspecified  task_id")
    parser.add_argument("--limit", "-l", type=int, default=0, help="only run top  N  case (0=full ) ")
    parser.add_argument("--max-concurrent", "-c", type=int, default=6, dest="max_concurrent", help="concurrency (default 6) ")
    parser.add_argument("--max-turns", "-t", type=int, default=10, dest="max_turns", help="max retrievalturns (default 10) ")
    parser.add_argument("--output-base", "-o", default="", dest="output_base", help="resultsoutputdirectory")
    parser.add_argument("--model", "-m", default="", dest="model", help="coveragemodelname (defaultuse  MODEL_CONFIG_GENERIC) ")
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
