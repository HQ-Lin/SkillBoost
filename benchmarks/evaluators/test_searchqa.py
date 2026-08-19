#!/usr/bin/env python3
import asyncio
import json
import os
import re
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path

from provider import (
    async_chat_completion,
    openai_compatible_api_key,
    openai_compatible_provider_label,
    provider_model,
)

                                                         
      
                                                         

                               
MODEL_CONFIG_GENERIC = {
    "model_provider": "openai-compatible",
    "model_name": "qwen3.7-max",
    "api_key_env": "LLM_API_KEY",
}

                 
ACTIVE_MODEL_CONFIG = MODEL_CONFIG_GENERIC

                                                         
           
                                                         

SYSTEM_PROMPT_TEMPLATE = """\
you  is one  answer correctness verificationexpert. you  task is judgecandidateanswer is whether correctanswered the given questions.

strictwith reviewrulethen :

{skill_content}
"""

USER_PROMPT_TEMPLATE = """\
judgewith candidateanswer is whether correctanswered the given questions.

【questions】
{question}

【searchcontext】
{context}

【candidateanswer】
{candidate_answer}

only output JSON formatresults (not require outputothercontent) :
{{"status": "correct"  or  "incorrect", "reason": "judge"}}"""

                                                         
        
                                                         

async def call_llm_api(messages: list, model_name: str, api_key: str) -> str:
    """call OpenAI-compatible API (diff steps, passed httpx) """
    import httpx

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        return data["choices"][0]["message"]["content"]

async def call_llm(messages: list, config: dict) -> str:
    """unified LLM call"""
    api_key = openai_compatible_api_key(config["api_key_env"])
    return await call_llm_api(messages, config["model_name"], api_key)

                                                         
      
                                                         

def parse_status(response_text: str) -> str:
    """from  LLM output in parse correct/incorrect/unknown"""
               
    json_match = re.search(r'\{[^{}]*"status"\s*:\s*"(correct|incorrect)"[^{}]*\}',
                           response_text, re.IGNORECASE | re.DOTALL)
    if json_match:
        return json_match.group(1).lower()

                
    text_lower = response_text.lower()
    if '"incorrect"' in text_lower or "'incorrect'" in text_lower:
        return "incorrect"
    if '"correct"' in text_lower or "'correct'" in text_lower:
        return "correct"

    return "unknown"

def parse_reason(response_text: str) -> str:
    """from  LLM output in extract reason"""
    m = re.search(r'"reason"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response_text)
    if m:
        reason = m.group(1).replace('\\"', '"').replace('\\n', ' ')
        return reason[:200] if len(reason) > 200 else reason
    return ""

                                                         
       
                                                         

async def evaluate_case(case: dict, system_prompt: str, semaphore: asyncio.Semaphore,
                        model_config: dict, traces_dir: Path, index: int, total: int) -> dict:
    """evaluationsingle   case"""
    async with semaphore:
        task_id = case["task_id"]

              
        user_prompt = USER_PROMPT_TEMPLATE.format(
            question=case["question"],
            context=case["context"],
            candidate_answer=case["candidate_answer"],
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

               
        ir = case["investigate_result"]
        gt_status = "correct" if ir == 1 else "incorrect"

        max_retries = 2
        last_error = None

        for retry in range(max_retries + 1):
            try:
                if retry > 0:
                    await asyncio.sleep(3 * retry)

                response_text = await call_llm(messages, model_config)
                agent_status = parse_status(response_text)
                reason = parse_reason(response_text)
                is_correct = agent_status == gt_status

                icon = ""if is_correct else (""if agent_status == "unknown"else "")
                print(f"  [{index}/{total}] {task_id}: GT={gt_status}, Pred={agent_status} {icon}")

                          
                trace_data = {
                    "task_id": task_id,
                    "messages": messages,
                    "response": response_text,
                    "parsed_status": agent_status,
                    "gt_status": gt_status,
                    "correct": is_correct,
                    "timestamp": datetime.now().isoformat(),
                }
                trace_file = traces_dir / f"trace_{task_id}.json"
                with open(trace_file, "w", encoding="utf-8") as f:
                    json.dump(trace_data, f, ensure_ascii=False, indent=2)

                return {
                    "task_id": task_id,
                    "gt": gt_status,
                    "agent": agent_status,
                    "correct": is_correct,
                    "reason": reason,
                    "result_text": response_text,
                    "trace_file": str(trace_file),
                    "gold_answers": case.get("gold_answers", []),
                    "candidate_answer": case["candidate_answer"],
                }

            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "Throttling" in error_str or "rate" in error_str.lower():
                    wait_time = 10 * (retry + 1)
                    print(f"  [{index}/{total}] {task_id}: rate limit, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                print(f"  [{index}/{total}] {task_id}:  error - {e}")
                break

        return {
            "task_id": task_id,
            "gt": gt_status,
            "agent": "error",
            "correct": False,
            "reason": "",
            "result_text": "",
            "error": str(last_error) if last_error else "Unknown error",
            "trace_file": None,
            "gold_answers": case.get("gold_answers", []),
            "candidate_answer": case["candidate_answer"],
        }

async def run_evaluation(args):
    """run evaluation"""
    print("=" * 70)
    print("SearchQA answer correctness verification - evaluation")
    print("=" * 70)

    model_config = dict(ACTIVE_MODEL_CONFIG)
    model_config["model_provider"] = openai_compatible_provider_label()
    model_config["model_name"] = provider_model(model_config["model_name"])
    print(f"\n model: {model_config['model_provider']} / {model_config['model_name']}")

              
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
        print(f"  filtered, test only {len(test_cases)}  specified  case")

    print(f"data: {len(test_cases)} cases from {jsonl_path}")

          
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output_base:
        output_base = Path(args.output_base)
        if not output_base.is_absolute():
            output_base = Path(__file__).parent.parent / output_base
    else:
        output_base = Path(__file__).parent.parent / "evolved" / "searchqa-verifier"

    dataset_name = Path(args.data).stem
    run_dir = output_base / f"{dataset_name}_run_{timestamp}"
    evals_dir = run_dir / "evals"
    traces_dir = run_dir / "traces"

    evals_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)

    print(f"output: {run_dir}")
    print(f"concurrency: {args.max_concurrent}")

          
    semaphore = asyncio.Semaphore(args.max_concurrent)
    start_time = time.time()

    tasks = [
        evaluate_case(case, system_prompt, semaphore, model_config, traces_dir, i + 1, len(test_cases))
        for i, case in enumerate(test_cases)
    ]
    results_data = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    print(f"\n  elapsed: {elapsed:.1f}s ({elapsed/len(test_cases):.2f}s/case)")

                                                      
    total = len(results_data)
    correct_count = sum(1 for r in results_data if r["correct"])
    error_count = sum(1 for r in results_data if r["agent"] == "error")
    unknown_count = sum(1 for r in results_data if r["agent"] == "unknown")
    effective_total = total - error_count - unknown_count

    accuracy = correct_count / total * 100 if total > 0 else 0
    effective_accuracy = correct_count / effective_total * 100 if effective_total > 0 else 0

              
    fp_count = sum(1 for r in results_data
                   if r["gt"] == "correct" and r["agent"] == "incorrect")
    fn_count = sum(1 for r in results_data
                   if r["gt"] == "incorrect" and r["agent"] == "correct")
    gt_correct_total = sum(1 for r in results_data if r["gt"] == "correct")
    gt_incorrect_total = sum(1 for r in results_data if r["gt"] == "incorrect")
    fp_rate = fp_count / gt_correct_total * 100 if gt_correct_total > 0 else 0
    fn_rate = fn_count / gt_incorrect_total * 100 if gt_incorrect_total > 0 else 0

    print(f"\n{'='*70}")
    print(f"evaluation results:")
    print(f"{'='*70}")
    print(f"  total case  count: {total}")
    print(f"  correct: {correct_count}")
    print(f"  error (judgment mismatch) : {total - correct_count - error_count - unknown_count}")
    print(f"  execution exception: {error_count}")
    print(f"  parse failed: {unknown_count}")
    print(f"  ──────────────────────")
    print(f"  accuracy (full set): {accuracy:.1f}%")
    print(f"  accuracy (valid ) : {effective_accuracy:.1f}%")
    print(f"  FP rate (correct→incorrect) : {fp_rate:.1f}% ({fp_count}/{gt_correct_total})")
    print(f"  FN rate (error→correct) : {fn_rate:.1f}% ({fn_count}/{gt_incorrect_total})")

                
    wrong_cases = [r for r in results_data if not r["correct"] and r["agent"] not in ("error", "unknown")]
    if wrong_cases:
        print(f"\n error case ({len(wrong_cases)}  ):")
        for wc in wrong_cases[:20]:             
            print(f"  {wc['task_id']}: GT={wc['gt']}, Pred={wc['agent']} | answer='{wc['candidate_answer']}' | {wc['reason'][:80]}")

                                                     
    result_file = evals_dir / f"results_{dataset_name}_{timestamp}.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results_data:
                                        
            save_r = {k: v for k, v in r.items() if k != "result_text"}
            f.write(json.dumps(save_r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "run_timestamp": timestamp,
        "model": f"{model_config['model_provider']}/{model_config['model_name']}",
        "skill_path": str(skill_path),
        "data_path": str(jsonl_path),
        "total": total,
        "correct": correct_count,
        "incorrect": total - correct_count - error_count - unknown_count,
        "error_count": error_count,
        "unknown_count": unknown_count,
        "effective_total": effective_total,
        "accuracy": round(accuracy, 2),
        "effective_accuracy": round(effective_accuracy, 2),
        "fp_count": fp_count,
        "fn_count": fn_count,
        "fp_rate": round(fp_rate, 2),
        "fn_rate": round(fn_rate, 2),
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
    parser = argparse.ArgumentParser(
        description="SearchQA answer correctness verification - batchevaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
show example:
  python benchmarks/evaluators/test_searchqa.py \\
      --data data/searchqa/train.jsonl \\
      --skill evolved/searchqa-verifier/v0 \\
      --max-concurrent 20 \\
      --output-base evolved/searchqa-verifier
        """
    )
    parser.add_argument("--data", "-d", required=True, help="datasetpath (.jsonl) ")
    parser.add_argument("--skill", "-s", required=True, help="Skill directorypath")
    parser.add_argument("--filter-ids", "-f", nargs="*", default=[], dest="filter_ids",
                        help="only evaluationspecified  task_id")
    parser.add_argument("--max-concurrent", "-c", type=int, default=20, dest="max_concurrent",
                        help="concurrencytask count (default 20) ")
    parser.add_argument("--output-base", "-o", default="", dest="output_base",
                        help="resultsoutputdirectory (default evolved/searchqa-verifier) ")

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
