#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

from bfcl_runtime import load_bfcl_runtime

                                                         
    
                                                         

API_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
API_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")
API_TIMEOUT = 300.0

BFCL_DATA_DIR: Path | None = None
FUNC_DOC_DIR: Path | None = None
POSSIBLE_ANSWER_DIR: Path | None = None
multi_turn_checker = None
execute_multi_turn_func_call = None

CATEGORIES = ["multi_turn_base", "multi_turn_miss_func", "multi_turn_miss_param", "multi_turn_long_context"]

CLASS_FILE_MAP = {
    "GorillaFileSystem": "gorilla_file_system.json",
    "MathAPI": "math_api.json",
    "MessageAPI": "message_api.json",
    "TwitterAPI": "posting_api.json",
    "TicketAPI": "ticket_api.json",
    "TradingBot": "trading_bot.json",
    "TravelAPI": "travel_booking.json",
    "VehicleControlAPI": "vehicle_control.json",
    "MemoryAPI_kv": "memory_kv.json",
    "MemoryAPI_vector": "memory_vector.json",
    "MemoryAPI_rec_sum": "memory_rec_sum.json",
    "WebSearchAPI": "web_search.json",
}

MAX_STEPS_PER_TURN = 20

_FUNC_DOC_CACHE: dict = {}

                                                         
           
                                                         

def _load_func_doc(file_name: str) -> list:
    if file_name in _FUNC_DOC_CACHE:
        return _FUNC_DOC_CACHE[file_name]
    if FUNC_DOC_DIR is None:
        raise RuntimeError("BFCL runtime has not been initialized")
    path = FUNC_DOC_DIR / file_name
    docs = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    docs.append(json.loads(line))
    _FUNC_DOC_CACHE[file_name] = docs
    return docs

def _doc_to_anthropic_tool(doc: dict) -> dict:
    """ func_doc convert as  Anthropic tool definitionformat. """
    params = doc.get("parameters", {})
    props = params.get("properties", {})
    required = params.get("required", [])

    clean_props = {}
    for pname, pinfo in props.items():
        schema = {"type": pinfo.get("type", "string")}
        if "description" in pinfo:
            schema["description"] = pinfo["description"]
        if "enum" in pinfo:
            schema["enum"] = pinfo["enum"]
        clean_props[pname] = schema

    tool = {
        "name": doc["name"],
        "description": doc.get("description", ""),
        "input_schema": {
            "type": "object",
            "properties": clean_props,
        },
    }
    if required:
        tool["input_schema"]["required"] = required
    return tool

def build_anthropic_tools(involved_classes: list, excluded: list) -> list:
    """build  Anthropic tools columntable. """
    excluded_set = set(excluded or [])
    tools = []
    seen = set()
    for cls in involved_classes or []:
        file_name = CLASS_FILE_MAP.get(cls)
        if not file_name:
            continue
        for doc in _load_func_doc(file_name):
            name = doc.get("name")
            if not name or name in excluded_set or name in seen:
                continue
            seen.add(name)
            tools.append(_doc_to_anthropic_tool(doc))
    return tools

def load_ground_truths(category: str) -> dict:
    if POSSIBLE_ANSWER_DIR is None:
        raise RuntimeError("BFCL runtime has not been initialized")
    path = POSSIBLE_ANSWER_DIR / f"BFCL_v4_{category}.json"
    if not path.exists():
        return {}
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return {r["id"]: r["ground_truth"] for r in records}

def load_test_entries(category: str) -> list:
    if BFCL_DATA_DIR is None:
        raise RuntimeError("BFCL runtime has not been initialized")
    path = BFCL_DATA_DIR / f"BFCL_v4_{category}.json"
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def convert_to_function_call(function_call_list):
    """modeloutput  [{name: args}] convert as can exec  linescharsstring listtable"""
    if isinstance(function_call_list, dict):
        function_call_list = [function_call_list]
    execution_list = []
    for function_call in function_call_list:
        for key, value in function_call.items():
            if isinstance(value, str):
                value = json.loads(value)
            execution_list.append(
                f"{key}({','.join([f'{k}={repr(v)}' for k, v in value.items()])})"
            )
    return execution_list

def load_skill(skill_path: Path) -> str:
    content = skill_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()
    return content

                                                         
                  
                                                         

async def call_anthropic(messages: list, system: str, tools: list,
                         model: str, max_retries: int = 5) -> dict:
    """call Anthropic Messages API,returned full response. """
    url = f"{API_BASE_URL.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 8192,
        "system": system,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = {"type": "auto"}

    last_err = None
    timeout_cfg = httpx.Timeout(API_TIMEOUT, connect=30.0)
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException,
                httpx.ReadTimeout, httpx.WriteError, httpx.RemoteProtocolError,
                httpx.HTTPStatusError) as e:
            last_err = e
            detail = ""
            if isinstance(e, httpx.HTTPStatusError):
                detail = f" status={e.response.status_code} body={e.response.text[:200]}"
            if attempt < max_retries:
                wait = min(3 ** attempt, 30)
                print(f"  {type(e).__name__}{detail},retry {attempt+1}/{max_retries}(wait {wait}s)", flush=True)
                await asyncio.sleep(wait)
            else:
                raise
    raise last_err

                                                         
                           
                                                         

async def run_case(
    test_entry: dict,
    ground_truth_list: list,
    system_prompt: str,
    semaphore: asyncio.Semaphore,
    model: str,
    traces_dir: Path,
    index: int,
    total: int,
) -> dict:
    async with semaphore:
        case_id = test_entry["id"]
        category = case_id.rsplit("_", 1)[0].replace("multi_turn_", "")
        involved = test_entry.get("involved_classes", [])
        excluded = test_entry.get("excluded_function", [])
        initial_config = test_entry.get("initial_config", {})
        turns = test_entry.get("question", [])

        tools = build_anthropic_tools(involved, excluded)

                            
        api_messages = []
        all_model_responses: list[list] = []
        trace_turns = []

        unique_model_name = f"eval_{case_id}_{int(time.time())}"

        try:
            for turn_idx, turn_msgs in enumerate(turns):
                for m in turn_msgs:
                    api_messages.append({
                        "role": m.get("role", "user"),
                        "content": m.get("content", ""),
                    })

                current_turn_responses = []
                turn_calls = []

                for step in range(MAX_STEPS_PER_TURN):
                    data = await call_anthropic(api_messages, system_prompt, tools, model)
                    content_blocks = data.get("content", [])

                                     
                    api_messages.append({"role": "assistant", "content": content_blocks})

                                        
                    tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
                    if not tool_uses:
                        break

                                                    
                    model_responses = []
                    for tu in tool_uses:
                        name = tu.get("name", "")
                        args = tu.get("input", {})
                        model_responses.append({name: json.dumps(args, ensure_ascii=False)})
                        turn_calls.append({"name": name, "arguments": json.dumps(args, ensure_ascii=False)})

                    current_turn_responses.append(model_responses)

                          
                    try:
                        exec_strings = convert_to_function_call(model_responses)
                        execution_results, _ = execute_multi_turn_func_call(
                            exec_strings,
                            initial_config,
                            involved,
                            unique_model_name,
                            case_id,
                            long_context=("long_context" in case_id),
                            is_evaL_run=False,
                        )
                    except Exception as exec_err:
                        execution_results = [f"Error: {str(exec_err)[:200]}"]

                                            
                    tool_results = []
                    for i, tu in enumerate(tool_uses):
                        result_str = execution_results[i] if i < len(execution_results) else "Error: no result"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu["id"],
                            "content": str(result_str),
                        })
                    api_messages.append({"role": "user", "content": tool_results})

                all_model_responses.append(current_turn_responses)
                trace_turns.append({"turn": turn_idx, "calls": turn_calls})

                                           
            multi_turn_decoded: list[list[list[str]]] = []
            for turn_responses in all_model_responses:
                turn_decoded = []
                for step_response in turn_responses:
                    try:
                        decoded = convert_to_function_call(step_response)
                        if decoded:
                            turn_decoded.append(decoded)
                    except Exception:
                        pass
                multi_turn_decoded.append(turn_decoded)

            check_result = multi_turn_checker(
                multi_turn_decoded,
                ground_truth_list,
                test_entry,
                category,
                unique_model_name + "_checker",
            )

            passed = check_result.get("valid", False)
            error_type = check_result.get("error_type", "") if not passed else ""
            error_msg = check_result.get("error_message", "") if not passed else ""

            icon = ""if passed else ""
            print(f"  [{index}/{total}] {case_id}: {icon} {error_type}", flush=True)

            trace = {
                "id": case_id,
                "category": category,
                "passed": passed,
                "error_type": error_type,
                "error_message": error_msg,
                "turns": trace_turns,
                "model_responses": all_model_responses,
                "ground_truth": ground_truth_list,
                "timestamp": datetime.now().isoformat(),
            }
            with open(traces_dir / f"trace_{case_id}.json", "w", encoding="utf-8") as f:
                json.dump(trace, f, ensure_ascii=False, indent=2, default=str)

            return {
                "id": case_id,
                "category": category,
                "passed": passed,
                "error_type": error_type,
                "error": "",
            }

        except Exception as e:
            err_str = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"  [{index}/{total}] {case_id}:  EXCEPTION: {err_str}", flush=True)
            return {
                "id": case_id,
                "category": category,
                "passed": False,
                "error_type": "exception",
                "error": err_str,
            }

                                                         
     
                                                         

async def run_evaluation(args):
    global BFCL_DATA_DIR, FUNC_DOC_DIR, POSSIBLE_ANSWER_DIR
    global multi_turn_checker, execute_multi_turn_func_call

    runtime = load_bfcl_runtime(getattr(args, "bfcl_data_dir", None))
    BFCL_DATA_DIR = runtime.data_dir
    FUNC_DOC_DIR = runtime.data_dir / "multi_turn_func_doc"
    POSSIBLE_ANSWER_DIR = runtime.data_dir / "possible_answer"
    multi_turn_checker = runtime.multi_turn_checker
    execute_multi_turn_func_call = runtime.execute_multi_turn_func_call
    _FUNC_DOC_CACHE.clear()

    print("=" * 70)
    print("BFCL-v4 multi-turn function calling evaluation(Claude  variant) - extra  100  items")
    print("=" * 70)

    model = args.model
    print(f"\n model: anthropic / {model}")
    print(f"Base URL: {API_BASE_URL}")

    skill_path = Path(args.skill)
    if not skill_path.exists():
        print(f"Skill file not found: {skill_path}")
        sys.exit(1)
    system_prompt = load_skill(skill_path)
    print(f"Skill: {skill_path}")

            
    exclude_ids = set()
    if args.exclude_file:
        with open(args.exclude_file, 'r') as f:
            evaluated_data = json.load(f)
            for cat, ids in evaluated_data.items():
                exclude_ids.update(ids)
        print(f"excluded already-evaluation  case: {len(exclude_ids)}  items")

             
    categories = args.category if "all" not in args.category else CATEGORIES
    all_ground_truths = {}
    cases = []

    for cat in categories:
        entries = load_test_entries(cat)
        gts = load_ground_truths(cat)
        all_ground_truths.update(gts)
        
                                          
        cat_cases = [(e, gts[e["id"]]) for e in entries if e["id"] in gts and e["id"] not in exclude_ids]
        
                                                    
        if args.limit > 0:
            per_cat = args.limit // len(categories)
            cat_cases = cat_cases[:per_cat]
        
        print(f"  {cat}: {len(entries)} total, excluded  {len(entries) - len(cat_cases)}  items, selected {len(cat_cases)} cases")
        cases.extend(cat_cases)

    print(f"total: {len(cases)} cases")

    output_dir = Path(args.output_dir)
    run_dir = output_dir / f"run_{args.run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    traces_dir = run_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    print(f"output: {run_dir}")
    print(f"concurrency: {args.concurrency}")

    semaphore = asyncio.Semaphore(args.concurrency)
    start = time.time()
    tasks = [
        run_case(entry, gt, system_prompt, semaphore, model, traces_dir, i + 1, len(cases))
        for i, (entry, gt) in enumerate(cases)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

              
    total_count = len(results)
    passed = sum(1 for r in results if r["passed"])
    errors = sum(1 for r in results if r.get("error"))
    accuracy = passed / total_count * 100 if total_count else 0

    print(f"\n{'='*70}")
    print(f"evaluation results(official  Accuracy)")
    print(f"{'='*70}")
    print(f"  total case: {total_count}, exception: {errors}")
    print(f"   passed: {passed}/{total_count}")
    print(f"   Accuracy: {accuracy:.2f}%")
    print(f"  elapsed: {elapsed:.1f}s")

    from collections import defaultdict
    cat_stats = defaultdict(lambda: {"total": 0, "passed": 0})
    error_type_stats = defaultdict(int)
    for r in results:
        cat = r.get("category", "unknown")
        cat_stats[cat]["total"] += 1
        if r["passed"]:
            cat_stats[cat]["passed"] += 1
        if not r["passed"] and r.get("error_type"):
            error_type_stats[r["error_type"]] += 1

    for cat, stats in sorted(cat_stats.items()):
        cat_acc = stats["passed"] / stats["total"] * 100 if stats["total"] else 0
        print(f"  [{cat}] n={stats['total']} accuracy={cat_acc:.1f}% ({stats['passed']}/{stats['total']})")

    if error_type_stats:
        print(f"\n  error type distribution:")
        for etype, count in sorted(error_type_stats.items(), key=lambda x: -x[1]):
            print(f"    {etype}: {count}")

    result_file = run_dir / "results.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "run_id": args.run_id,
        "model": f"anthropic/{model}",
        "skill_path": str(skill_path),
        "categories": categories,
        "total": total_count,
        "passed": passed,
        "accuracy": round(accuracy, 2),
        "error_count": errors,
        "elapsed_seconds": round(elapsed, 1),
        "by_category": {
            cat: {
                "n": stats["total"],
                "passed": stats["passed"],
                "accuracy": round(stats["passed"] / stats["total"] * 100 if stats["total"] else 0, 2),
            } for cat, stats in cat_stats.items()
        },
        "error_types": dict(error_type_stats),
    }
    with open(run_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n results: {result_file}")
    print(f"report: {run_dir / 'report.json'}")
    print("=" * 70)
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BFCL-v4 Claude official evaluation(extra  100  items)")
    parser.add_argument("--skill", required=True, help="Skill filepath (SKILL.md)")
    parser.add_argument("--concurrency", type=int, default=2, help="concurrency(provider-router suggestion 20)")
    parser.add_argument("--run_id", default="run", help="run identifier")
    parser.add_argument("--output_dir", required=True, help="output directory")
    parser.add_argument("--limit", type=int, default=0, help="limitevaluation items count(0=full )")
    parser.add_argument("--model", default="claude-opus-4-6", help="modelname")
    parser.add_argument("--category", nargs="+", default=["all"], help="evaluationclass,can multi-pass : multi_turn_base / miss_func / miss_param / long_context")
    parser.add_argument("--exclude_file", type=str, help="evaluation case ID  JSON filepath")
    parser.add_argument(
        "--bfcl-data-dir",
        default="",
        help="optional BFCL data override; defaults to data bundled with bfcl-eval",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    for attr in ("skill", "output_dir"):
        p = getattr(args, attr)
        if p and not Path(p).is_absolute():
            setattr(args, attr, str(project_root / p))

    asyncio.run(run_evaluation(args))
