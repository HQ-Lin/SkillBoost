#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from provider import (
    async_chat_completion,
    openai_compatible_api_key,
    openai_compatible_provider_label,
    provider_model,
)

                                                         
      
                                                         
MODEL_CONFIG = {
    "model_name": "qwen3.7-max",
    "api_key_env": "LLM_API_KEY",
}

SYSTEM_PROMPT_TEMPLATE = """\
You are an expert mathematician solving challenging olympiad-level mathematics problems.

{skill_content}

You will receive a mathematics problem. Carefully analyze the problem, reason step by step, 
and provide a clear final answer.

Important:
- Think carefully about the problem conditions and constraints
- Show your reasoning process
- Output your final answer inside <answer>...</answer> tags
- If the answer is a number, provide it in simplest form
- If the answer is an expression, provide it in standard mathematical notation
- Do not include extra text inside the <answer> tags"""

USER_TEXT_TEMPLATE = """\
## Problem
{question}

## Answer Type
{answer_type}

Please solve this problem step by step, then provide your final answer inside <answer>...</answer>."""

                                                         
                                         
                                                         
def normalize_answer(text: str) -> str:
    """normalized answer: remove LaTeX symbol, empty, large  etc. """
    if not text:
        return ""
    
            
    text = str(text).strip()
    
                   
    text = text.replace("$", "").replace("\\[", "").replace("\\]", "")
    text = text.replace("\\(", "").replace("\\)", "")
    
                     
    text = text.replace("\\", "")
    
          
    text = text.replace(" ", "").replace("\t", "").replace("\n", "")
    
           
    text = text.lower()
    
            
    text = text.rstrip(".:,;")
    
    return text

def extract_answer(text: str) -> str:
    """from modeloutput in extract <answer> labelin  content. """
                      
    matches = re.findall(r"<answer>(.*?)</answer>", text, re.DOTALL | re.IGNORECASE)
    if matches:
                           
        return matches[-1].strip()
    
                                     
    patterns = [
        r"(?:^|\n)\s*Answer\s*:\s*(.+?)(?:\n|$)",
        r"(?:^|\n)\s*The answer is\s+(.+?)(?:\n|$)",
        r"(?:^|\n)\s*Therefore\s*,?\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[-1].strip()
    
                 
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if lines:
        return lines[-1]
    
    return text.strip()

def em_evaluate(prediction_text: str, correct_answer: str, answer_type: str = "Numerical") -> dict:
    """
    Exact Match scoring.
    
    for at  countvalueanswer,  linesstrict  countvaluecompare.
    for at tableanswer,  linescharsstringmatch (formatdifference) .
    """
    predicted = extract_answer(prediction_text)
    pred_norm = normalize_answer(predicted)
    gold_norm = normalize_answer(correct_answer)
    
          
    exact_match = int(pred_norm == gold_norm)
    
                             
    numerical_match = 0
    if answer_type == "Numerical":
        try:
                    
            pred_nums = re.findall(r"[\d.]+", pred_norm)
            gold_nums = re.findall(r"[\d.]+", gold_norm)
            if pred_nums and gold_nums:
                pred_val = float(pred_nums[-1])
                gold_val = float(gold_nums[-1])
                         
                numerical_match = int(abs(pred_val - gold_val) < 1e-6)
        except (ValueError, IndexError):
            pass
    
                       
    score = max(exact_match, numerical_match)
    
    return {
        "em": score,
        "exact_match": exact_match,
        "numerical_match": numerical_match,
        "predicted_answer": predicted,
        "correct_answer": correct_answer,
        "predicted_normalized": pred_norm,
        "correct_normalized": gold_norm,
    }

                                                         
        
                                                         
async def call_llm_api(messages: list, api_key: str, client, enable_thinking: bool = False) -> str:
    """call OpenAI-compatible API. """
    import httpx
    
    payload = {
        "model": MODEL_CONFIG["model_name"],
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 32768,
    }
    
                    
    if not enable_thinking:
        payload["enable_thinking"] = False
    
    async with httpx.AsyncClient(timeout=1800.0) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
                                                    
        if not content.strip():
            content = msg.get("reasoning_content") or ""
        if not content.strip():
            raise RuntimeError("empty completion content")
        return content

                                                         
       
                                                         
async def evaluate_case(case, system_prompt, semaphore, api_key, traces_dir, index, total, client, enable_thinking=False):
    """evaluationsingle  example. """
    task_id = case["task_id"]
    
    async with semaphore:
        print(f"[{index+1}/{total}] Processing {task_id}...")
        
                
        user_text = USER_TEXT_TEMPLATE.format(
            question=case["question"],
            answer_type=case.get("answer_type", "Numerical"),
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
        
        try:
            start_time = time.time()
            response = await call_llm_api(messages, api_key, client, enable_thinking=enable_thinking)
            elapsed = time.time() - start_time
            
                
            result = em_evaluate(
                response,
                case["final_answer"],
                case.get("answer_type", "Numerical"),
            )
            
                      
            trace = {
                "task_id": task_id,
                "question": case["question"],
                "correct_answer": case["final_answer"],
                "model_response": response,
                "prediction": result["predicted_answer"],
                "score": result["em"],
                "elapsed_seconds": elapsed,
            }
            
            trace_path = traces_dir / f"trace_{task_id}.json"
            with trace_path.open("w", encoding="utf-8") as f:
                json.dump(trace, f, indent=2, ensure_ascii=False)
            
            status = "✓" if result["em"] else "✗"
            print(f"  {status} {task_id}: score={result['em']}, time={elapsed:.1f}s")
            
            return {
                "task_id": task_id,
                "score": result["em"],
                "predicted": result["predicted_answer"],
                "correct": case["final_answer"],
                "elapsed": elapsed,
            }
            
        except Exception as e:
            print(f"  ✗ {task_id}: ERROR - {str(e)}")
            return {
                "task_id": task_id,
                "score": 0,
                "predicted": "",
                "correct": case["final_answer"],
                "error": str(e),
                "elapsed": 0,
            }

async def evaluate_case_with_timeout(case, system_prompt, semaphore, api_key, traces_dir, index, total, client, timeout=1800.0, enable_thinking=False):
    """with timeout evaluationfunction count. """
    try:
        return await asyncio.wait_for(
            evaluate_case(case, system_prompt, semaphore, api_key, traces_dir, index, total, client, enable_thinking=enable_thinking),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        task_id = case["task_id"]
        print(f"  ✗ {task_id}: TIMEOUT ({timeout}s)")
        return {
            "task_id": task_id,
            "score": 0,
            "predicted": "",
            "correct": case["final_answer"],
            "error": f"timeout ({timeout}s)",
            "elapsed": timeout,
        }

async def run_evaluation(data_path, skill_path, max_concurrent, output_base, task_timeout, enable_thinking=False):
    MODEL_CONFIG["model_name"] = provider_model(MODEL_CONFIG["model_name"])
    """run fullevaluation. """
    import httpx
    
          
    with Path(data_path).open(encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]
    
    print(f"Loaded {len(cases)} cases from {data_path}")
    
              
    skill_content = ""
    if skill_path and Path(skill_path).exists():
        skill_md = Path(skill_path) / "SKILL.md"
        if skill_md.exists():
            skill_content = skill_md.read_text(encoding="utf-8")
            print(f"Loaded skill from {skill_md}")
        else:
            print(f"Warning: SKILL.md not found in {skill_path}")
    
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(skill_content=skill_content)
    
            
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output_base) / f"test_run_{timestamp}"
    traces_dir = run_dir / "traces"
    evals_dir = run_dir / "evals"
    traces_dir.mkdir(parents=True, exist_ok=True)
    evals_dir.mkdir(parents=True, exist_ok=True)
    
             
    api_key = openai_compatible_api_key(MODEL_CONFIG["api_key_env"])
    
          
    semaphore = asyncio.Semaphore(max_concurrent)
    
          
    print(f"\nStarting evaluation with {max_concurrent} concurrent workers...")
    print(f"Model: {MODEL_CONFIG['model_name']}")
    print(f"Task timeout: {task_timeout}s")
    print(f"Thinking mode: {'ON' if enable_thinking else 'OFF (off)'}\n")
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for idx, case in enumerate(cases):
            task = evaluate_case_with_timeout(
                case, system_prompt, semaphore, api_key, traces_dir,
                idx, len(cases), client, timeout=task_timeout,
                enable_thinking=enable_thinking,
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
          
    valid_results = []
    error_count = 0
    
    for r in results:
        if isinstance(r, Exception):
            error_count += 1
            continue
        valid_results.append(r)
        if r.get("error"):
            error_count += 1
    
          
    total = len(valid_results)
    correct = sum(1 for r in valid_results if r["score"] == 1)
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"Evaluation Complete")
    print(f"{'='*60}")
    print(f"Total cases: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Errors: {error_count}")
    
                   
    subfield_stats = {}
    for r in valid_results:
        task_id = r["task_id"]
                             
        case = next((c for c in cases if c["task_id"] == task_id), None)
        if case:
            subfield = case.get("subfield", "Unknown")
            if subfield not in subfield_stats:
                subfield_stats[subfield] = {"total": 0, "correct": 0}
            subfield_stats[subfield]["total"] += 1
            subfield_stats[subfield]["correct"] += r["score"]
    
    print(f"\nAccuracy by Subfield:")
    for subfield, stats in sorted(subfield_stats.items()):
        acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {subfield}: {acc:.1f}% ({stats['correct']}/{stats['total']})")
    
          
    report = {
        "timestamp": datetime.now().isoformat(),
        "model": f"{openai_compatible_provider_label()}/{MODEL_CONFIG['model_name']}",
        "skill_path": str(skill_path) if skill_path else None,
        "data_path": str(data_path),
        "total": total,
        "error_count": error_count,
        "correct": correct,
        "accuracy": round(accuracy, 2),
        "subfield_accuracy": {
            k: round((v["correct"] / v["total"] * 100) if v["total"] > 0 else 0, 2)
            for k, v in subfield_stats.items()
        },
        "elapsed_seconds": sum(r.get("elapsed", 0) for r in valid_results),
        "results_file": str(evals_dir / f"results_{Path(data_path).stem}_{timestamp}.jsonl"),
        "traces_dir": str(traces_dir),
        "run_dir": str(run_dir),
    }
    
    report_path = evals_dir / f"report_{Path(data_path).stem}_{timestamp}.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
            
    results_path = evals_dir / f"results_{Path(data_path).stem}_{timestamp}.jsonl"
    with results_path.open("w", encoding="utf-8") as f:
        for r in valid_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    print(f"\nReport saved to: {report_path}")
    print(f"Results saved to: {results_path}")
    
    return report

def main():
    parser = argparse.ArgumentParser(description="OlympiadBench evaluationscript")
    parser.add_argument("--data", type=str, required=True, help="datasetpath (jsonl)")
    parser.add_argument("--skill", type=str, default="", help="Skill directorypath")
    parser.add_argument("--model", type=str, default=None, help="coveragemodelnamename")
    parser.add_argument("--max-concurrent", type=int, default=10, help="max concurrency")
    parser.add_argument("--task-timeout", type=int, default=1800, help="single  questionstimeout () ")
    parser.add_argument("--output-base", type=str, default="evolved/olympiadbench-solver", help="outputbase directory")
    parser.add_argument("--enable-thinking", action="store_true", dest="enable_thinking", default=False,
                       help="onthinking mode (defaultoff, with speedupevaluation) ")
    args = parser.parse_args()
    
            
    if args.model:
        MODEL_CONFIG["model_name"] = args.model
    
    print("="*60)
    print("OlympiadBench Evaluation")
    print("="*60)
    print(f"Model: {MODEL_CONFIG['model_name']}")
    print(f"Data: {args.data}")
    print(f"Skill: {args.skill}")
    print(f"Max concurrent: {args.max_concurrent}")
    print(f"Task timeout: {args.task_timeout}s")
    print(f"Thinking mode: {'ON' if args.enable_thinking else 'OFF (off)'}")
    print("="*60)
    
          
    report = asyncio.run(run_evaluation(
        args.data,
        args.skill,
        args.max_concurrent,
        args.output_base,
        args.task_timeout,
        enable_thinking=args.enable_thinking,
    ))
    
    print(f"\n{'='*60}")
    print(f"Final Accuracy: {report['accuracy']:.2f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
