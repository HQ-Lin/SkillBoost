#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from bfcl_runtime import load_bfcl_runtime
from provider import (
    async_chat_completion,
    openai_compatible_api_key,
    openai_compatible_provider_label,
    provider_model,
)

                                                         
    
                                                         

MODEL_CONFIG = {
    "backend": "openai_compatible",                                  
    "model_name": "qwen3.7-max",
    "api_key_env": "LLM_API_KEY",
}

BFCL_DATA_DIR: Path | None = None
FUNC_DOC_DIR: Path | None = None
POSSIBLE_ANSWER_DIR: Path | None = None
multi_turn_checker = None
execute_multi_turn_func_call = None

CATEGORIES = ["multi_turn_base", "multi_turn_miss_func", "multi_turn_miss_param", "multi_turn_long_context"]

MULTI_TURN_FUNC_DOC_FILE_MAPPING = {
    "GorillaFileSystem": "gorilla_file_system.json",
    "MathAPI": "math_api.json",
    "MessageAPI": "message_api.json",
    "TwitterAPI": "posting_api.json",
    "TicketAPI": "ticket_api.json",
    "TradingBot": "trading_bot.json",
    "TravelAPI": "travel_booking.json",
    "VehicleControlAPI": "vehicle_control.json",
    "WebSearchAPI": "web_search.json",
}

TYPE_MAP = {
    "dict": "object", "object": "object",
    "string": "string", "str": "string",
    "integer": "integer", "int": "integer",
    "number": "number", "float": "number", "double": "number",
    "boolean": "boolean", "bool": "boolean",
    "array": "array", "list": "array", "tuple": "array",
    "any": "string",
}

MAX_STEPS_PER_TURN = 20                  

_FUNC_DOC_CACHE: dict = {}

                                                         
      
                                                         

def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def load_func_doc(file_name: str) -> list[dict]:
    if file_name in _FUNC_DOC_CACHE:
        return _FUNC_DOC_CACHE[file_name]
    if FUNC_DOC_DIR is None:
        raise RuntimeError("BFCL runtime has not been initialized")
    path = FUNC_DOC_DIR / file_name
    docs = load_jsonl(path)
    _FUNC_DOC_CACHE[file_name] = docs
    return docs

def _clean_schema(node):
    if not isinstance(node, dict):
        return {"type": "string"}
    out = {}
    raw_type = node.get("type")
    if isinstance(raw_type, str):
        out["type"] = TYPE_MAP.get(raw_type.lower(), "string")
    if "description" in node and isinstance(node["description"], str):
        out["description"] = node["description"]
    if "enum" in node:
        out["enum"] = node["enum"]
    props = node.get("properties")
    if isinstance(props, dict):
        out["type"] = "object"
        out["properties"] = {k: _clean_schema(v) for k, v in props.items()}
    if "required" in node and isinstance(node["required"], list):
        out["required"] = node["required"]
    if out.get("type") == "array":
        items = node.get("items")
        out["items"] = _clean_schema(items) if isinstance(items, dict) else {"type": "string"}
    return out

def build_tools(involved_classes: list, excluded: list = None) -> list:
    excluded_set = set(excluded or [])
    tools = []
    seen = set()
    for cls in involved_classes or []:
        file_name = MULTI_TURN_FUNC_DOC_FILE_MAPPING.get(cls)
        if not file_name:
            continue
        for doc in load_func_doc(file_name):
            name = doc.get("name")
            if not name or name in excluded_set or name in seen:
                continue
            seen.add(name)
            params = _clean_schema(doc.get("parameters", {}))
            if params.get("type") != "object":
                params = {"type": "object", "properties": {}}
            params.setdefault("properties", {})
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": (doc.get("description", "") or "")[:1024],
                    "parameters": params,
                },
            })
    return tools

def load_ground_truths(category: str) -> dict:
    """load possible_answer  in   ground truth, returned  {id: ground_truth_list}"""
    if POSSIBLE_ANSWER_DIR is None:
        raise RuntimeError("BFCL runtime has not been initialized")
    path = POSSIBLE_ANSWER_DIR / f"BFCL_v4_{category}.json"
    if not path.exists():
        return {}
    records = load_jsonl(path)
    return {r["id"]: r["ground_truth"] for r in records}

def load_test_entries(category: str) -> list[dict]:
    """loadofficial dataset"""
    if BFCL_DATA_DIR is None:
        raise RuntimeError("BFCL runtime has not been initialized")
    path = BFCL_DATA_DIR / f"BFCL_v4_{category}.json"
    if not path.exists():
        return []
    return load_jsonl(path)

                                                         
                       
                                                         

async def call_llm_api(messages: list, model_name: str, api_key: str,
                         tools: list = None, timeout: float = 600.0) -> dict:
    import httpx
    payload = {"model": model_name, "messages": messages, "temperature": 0.1, "max_tokens": 8192}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        return data["choices"][0]["message"]

async def call_anthropic(messages: list, model_name: str, api_key: str,
                         tools: list = None, timeout: float = 600.0) -> dict:
    """Call Anthropic Claude API via provider-router proxy."""
    import httpx
    base_url = MODEL_CONFIG.get("base_url", "https://api.anthropic.com")
    url = f"{base_url.rstrip('/')}/v1/messages"
    
                           
    system_prompt = ""
    actual_messages = messages
    if messages and messages[0].get("role") == "system":
        system_prompt = messages[0]["content"]
        actual_messages = messages[1:]
    
                   
    payload = {
        "model": model_name,
        "messages": actual_messages,
        "max_tokens": 8192,
        "temperature": 0.1,
    }
    if system_prompt:
        payload["system"] = system_prompt
    
                                                                             
                                                        
    if tools:
        tool_desc = "\n\nAvailable functions:\n" + "\n".join(
            f"- {t['function']['name']}: {t['function'].get('description', '')}" 
            for t in tools
        )
        payload["system"] = payload.get("system", "") + tool_desc
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [{}])[0].get("text", "")
        return {"role": "assistant", "content": content}

async def call_with_retry(messages, model_name, api_key, tools, max_retries=3):
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                await asyncio.sleep(min(2 ** attempt, 15))
                                      
            return await call_llm_api(messages, model_name, api_key, tools)
        except Exception as e:
            last_err = e
            print(f"      APIcall failed({type(e).__name__}: {str(e)[:100]}), retry {attempt + 1}/{max_retries}", flush=True)
    raise last_err

def convert_to_function_call(function_call_list):
    """modeloutput  [{name: args_json}] convert as can exec  linescharsstring listtable"""
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

                                                         
              
                                                         

async def run_case(
    test_entry: dict,
    ground_truth_list: list,
    system_prompt: str,
    model_name: str,
    api_key: str,
    semaphore: asyncio.Semaphore,
    traces_dir: Path,
    index: int,
    total: int,
) -> dict:
    async with semaphore:
        case_id = test_entry["id"]
        category = case_id.rsplit("_", 1)[0].replace("multi_turn_", "")
        involved_classes = test_entry.get("involved_classes", [])
        excluded = test_entry.get("excluded_function", [])
        initial_config = test_entry.get("initial_config", {})
        turns = test_entry.get("question", [])

        tools = build_tools(involved_classes, excluded)
        messages = [{"role": "system", "content": system_prompt}]

                                          
        all_model_responses: list[list] = []
        trace_turns = []
        err_str = ""

                      
        unique_model_name = f"eval_{case_id}_{int(time.time())}"

        try:
            for turn_idx, turn_msgs in enumerate(turns):
                        
                for m in turn_msgs:
                    messages.append({"role": m.get("role", "user"),
                                     "content": m.get("content", "")})

                current_turn_responses = []
                turn_calls = []

                for step in range(MAX_STEPS_PER_TURN):
                    msg = await call_with_retry(messages, model_name, api_key, tools)

                                        
                    assistant_msg = {"role": "assistant", "content": msg.get("content") or ""}
                    if msg.get("tool_calls"):
                        assistant_msg["tool_calls"] = msg["tool_calls"]
                    messages.append(assistant_msg)

                    tool_calls = msg.get("tool_calls") or []
                    if not tool_calls:
                        break

                                      
                    model_responses = []
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        args_str = fn.get("arguments") or "{}"
                        model_responses.append({name: args_str})
                        turn_calls.append({"name": name, "arguments": args_str})

                    current_turn_responses.append(model_responses)

                                   
                    try:
                        exec_strings = convert_to_function_call(model_responses)
                        execution_results, _ = execute_multi_turn_func_call(
                            exec_strings,
                            initial_config,
                            involved_classes,
                            unique_model_name,
                            case_id,
                            long_context=("long_context" in case_id),
                            is_evaL_run=False,
                        )
                    except Exception as exec_err:
                        execution_results = [f"Error: {str(exec_err)[:200]}"]

                                  
                    for i, tc in enumerate(tool_calls):
                        result_str = execution_results[i] if i < len(execution_results) else "Error: no result"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "content": str(result_str),
                        })

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

                                                         
          
                                                         

def load_skill(skill_path: Path) -> str:
    content = skill_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()
    return content

                                                         
     
                                                         

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
    print("BFCL-v4 multi-turn function calling evaluation (official evaluation variant - real execution + state check)")
    print("=" * 70)

    model_name = provider_model(args.model)
                                                                         
    if MODEL_CONFIG.get("backend") == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("environment variable ANTHROPIC_API_KEY is not set")
    else:
        api_key = openai_compatible_api_key(MODEL_CONFIG["api_key_env"])

    print(f"\n model: {model_name}")

    skill_path = Path(args.skill)
    if not skill_path.exists():
        print(f"Skill file not found: {skill_path}")
        sys.exit(1)
    system_prompt = load_skill(skill_path)
    print(f"Skill: {skill_path}")

          
    categories = [args.category] if args.category != "all" else CATEGORIES
    all_entries = []
    all_ground_truths = {}

    for cat in categories:
        entries = load_test_entries(cat)
        gts = load_ground_truths(cat)
        print(f"   {cat}: {len(entries)} entries, {len(gts)} ground truths")
        all_entries.extend(entries)
        all_ground_truths.update(gts)

                          
    cases = [(e, all_ground_truths[e["id"]]) for e in all_entries if e["id"] in all_ground_truths]

    if getattr(args, 'case_ids_file', '') and args.case_ids_file:
        with open(args.case_ids_file) as f:
            filter_ids = {line.strip() for line in f if line.strip()}
        cases = [(e, gt) for e, gt in cases if e["id"] in filter_ids]
        print(f"  filterto  {len(cases)} cases (from  {args.case_ids_file}) ")

    if args.limit > 0:
        cases = cases[:args.limit]
        print(f"    truncated to first  {len(cases)} cases")
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
        run_case(entry, gt, system_prompt, model_name, api_key, semaphore,
                 traces_dir, i + 1, len(cases))
        for i, (entry, gt) in enumerate(cases)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

              
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    errors = sum(1 for r in results if r.get("error"))
    accuracy = passed / total * 100 if total else 0

    print(f"\n{'='*70}")
    print(f"evaluation results (official Accuracy) ")
    print(f"{'='*70}")
    print(f"  total case: {total}, exception: {errors}")
    print(f"   passed: {passed}/{total}")
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
        "model": model_name,
        "skill_path": str(skill_path),
        "categories": categories,
        "total": total,
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
    parser = argparse.ArgumentParser(description="BFCL-v4 official evaluation variant")
    parser.add_argument("--skill", required=True, help="Skill filepath (SKILL.md)")
    parser.add_argument("--concurrency", type=int, default=5, help="concurrency")
    parser.add_argument("--run_id", default="run", help="run identifier")
    parser.add_argument("--output_dir", required=True, help="output directory")
    parser.add_argument("--limit", type=int, default=0, help="limitevaluation items count (0=full ) ")
    parser.add_argument("--model", default="qwen3.7-max", help="modelname")
    parser.add_argument("--backend", choices=["openai_compatible", "anthropic"], default="openai_compatible",
                        help="LLM backend: openai_compatible  or  anthropic")
    parser.add_argument("--category", default="all", help="evaluationclass (default all) ")
    parser.add_argument("--case-ids-file", default="", help="only evaluationspecified  case ID columntablefile (per  linesone  ID) ")
    parser.add_argument(
        "--bfcl-data-dir",
        default="",
        help="optional BFCL data override; defaults to data bundled with bfcl-eval",
    )
    args = parser.parse_args()

                       
    if args.backend == "anthropic":
        os.environ["SKILLBOOST_LLM_PROVIDER"] = "anthropic"
        MODEL_CONFIG["backend"] = "anthropic"
        MODEL_CONFIG["model_name"] = args.model
        MODEL_CONFIG["api_key_env"] = "ANTHROPIC_API_KEY"
        MODEL_CONFIG["base_url"] = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        print(f"model: anthropic / {args.model}")
    else:
        MODEL_CONFIG["model_name"] = args.model
        print(f"model: {openai_compatible_provider_label()} / {args.model}")

    project_root = Path(__file__).parent.parent
    for attr in ("skill", "output_dir"):
        p = getattr(args, attr)
        if p and not Path(p).is_absolute():
            setattr(args, attr, str(project_root / p))

    asyncio.run(run_evaluation(args))
