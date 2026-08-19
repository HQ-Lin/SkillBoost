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
    "model_name": "qwen3.6-plus",
    "api_key_env": "LLM_API_KEY",
}

SYSTEM_PROMPT_TEMPLATE = """\
You are an expert mathematical reasoning agent solving multiple-choice questions.

{skill_content}

You will receive one mathematics multiple-choice question and its answer choices.
Reason carefully about quantifiers, hypotheses, extremal wording, and exact equality conditions.
Think step by step, then provide your final answer inside <answer>...</answer> tags.
Inside the tags, output only the single choice label, such as A or C."""

USER_TEXT_TEMPLATE = """\
## Question
{question}

## Choices
{choices}

Think step by step, then output only the final choice label inside <answer>...</answer>."""

                                                         
                                           
                                                         
def normalize_label(text: str) -> str:
    return str(text).strip().upper().rstrip(".):")

def extract_answer(text: str) -> str:
    matches = re.findall(r"<answer>(.*?)</answer>", text, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[-1].strip()
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if lines:
        return lines[-1]
    return text.strip()

def parse_choice_label(prediction_text: str, choices: list) -> str:
    answer = extract_answer(prediction_text)
    label = normalize_label(answer)
    valid_labels = {normalize_label(c.get("label", "")) for c in choices}
    if label in valid_labels:
        return label

    answer_lower = answer.lower()
    for c in choices:
        choice_text = str(c.get("text", "")).strip()
        if choice_text and choice_text.lower() == answer_lower:
            return normalize_label(c.get("label", ""))

    first_token = normalize_label(answer.split()[0]) if answer.split() else ""
    if first_token in valid_labels:
        return first_token
    return label

def em_evaluate(prediction_text: str, correct_label: str, choices: list) -> dict:
    predicted_label = parse_choice_label(prediction_text, choices)
    gold = normalize_label(correct_label)
    predicted_text = ""
    for c in choices:
        if normalize_label(c.get("label", "")) == predicted_label:
            predicted_text = str(c.get("text", "")).strip()
            break
    return {
        "em": int(predicted_label == gold),
        "predicted_label": predicted_label,
        "predicted_text": predicted_text,
        "correct_label": gold,
    }

def format_choices(choices: list) -> str:
    return "\n".join(f"{c['label']}. {c['text']}" for c in choices)

                                                         
        
                                                         
async def call_llm_api(messages: list, api_key: str, client) -> tuple:
    payload = {
        "model": MODEL_CONFIG["model_name"],
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 32768,
    }
                                                      
    if MODEL_CONFIG.get("backend") == "openai_compatible":
        payload["enable_thinking"] = False
    data = await async_chat_completion(client, payload, api_key=api_key)
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
                                                                   
                                                                  
    if not content.strip():
        content = msg.get("reasoning_content") or ""
    if not content.strip():
        raise RuntimeError("empty completion content")
    usage = data.get("usage", {})
    return content, usage

async def call_anthropic(messages: list, api_key: str, client) -> tuple:
    """Call Anthropic Claude API (compatible with provider-router proxy)."""
                                                                      
    system_prompt = ""
    actual_messages = messages
    if messages and messages[0].get("role") == "system":
        system_prompt = messages[0]["content"]
        actual_messages = messages[1:]
    
                                 
    payload = {
        "model": MODEL_CONFIG["model_name"],
        "max_tokens": 32768,
        "temperature": 0.1,
        "messages": actual_messages
    }
    if system_prompt:
        payload["system"] = system_prompt
    
                                                       
    base_url = MODEL_CONFIG.get("base_url", "https://api.anthropic.com")
    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    resp = await client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    
    content = data.get("content", [{}])[0].get("text", "")
    usage = {
        "input_tokens": data.get("usage", {}).get("input_tokens", 0),
        "output_tokens": data.get("usage", {}).get("output_tokens", 0)
    }
    return content, usage

                                                         
       
                                                         
async def evaluate_case_with_timeout(case, system_prompt, semaphore, api_key, traces_dir, index, total, client, timeout=900.0):
    """with single  questionstimeoutcontrol evaluationfunction count, prevent any  examplehang and block the whole runprogress"""
    task_id = case["task_id"]
    try:
                                        
        result = await asyncio.wait_for(
            evaluate_case(case, system_prompt, semaphore, api_key, traces_dir, index, total, client),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        print(f"  [{index}/{total}] {task_id}:   timeout (>{timeout:.0f}s) , skipped", flush=True)
                    
        trace = {
            "task_id": task_id,
            "question": case["question"],
            "choices": case["choices"],
            "theorem_type": case.get("theorem_type", []),
            "response": "",
            "predicted_label": "",
            "predicted_text": "",
            "correct_label": case.get("correct_label", ""),
            "correct_text": case.get("correct_text", ""),
            "hard": 0,
            "timeout": True,
            "timeout_seconds": timeout,
            "timestamp": datetime.now().isoformat(),
        }
        (traces_dir / f"trace_{task_id}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return {
            "task_id": task_id,
            "question": case["question"],
            "predicted_label": "",
            "predicted_text": "",
            "correct_label": normalize_label(case.get("correct_label", "")),
            "correct_text": case.get("correct_text", ""),
            "theorem_type": case.get("theorem_type", []),
            "hard": 0,
            "agent": "timeout",
            "error": f"Timeout after {timeout:.0f}s",
        }

async def evaluate_case(case, system_prompt, semaphore, api_key, traces_dir, index, total, client):
    async with semaphore:
        task_id = case["task_id"]
        choices = case["choices"]
        correct_label = case["correct_label"]
        user_text = USER_TEXT_TEMPLATE.format(
            question=case["question"], choices=format_choices(choices))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

        max_retries = 3
        last_error = None
        for retry in range(max_retries + 1):
            try:
                if retry > 0:
                    await asyncio.sleep(5 * retry)
                                          
                if MODEL_CONFIG.get("backend") == "anthropic":
                    response_text, usage = await call_anthropic(messages, api_key, client)
                else:
                    response_text, usage = await call_llm_api(messages, api_key, client)
                ev = em_evaluate(response_text, correct_label, choices)
                hard = ev["em"]
                icon = ""if hard else ""
                print(f"  [{index}/{total}] {task_id}: pred={ev['predicted_label']} "
                      f"gold={ev['correct_label']} {icon}", flush=True)

                trace = {
                    "task_id": task_id,
                    "question": case["question"],
                    "choices": choices,
                    "theorem_type": case.get("theorem_type", []),
                    "response": response_text,
                    "predicted_label": ev["predicted_label"],
                    "predicted_text": ev["predicted_text"],
                    "correct_label": ev["correct_label"],
                    "correct_text": case.get("correct_text", ""),
                    "hard": hard,
                    "usage": usage,
                    "timestamp": datetime.now().isoformat(),
                }
                (traces_dir / f"trace_{task_id}.json").write_text(
                    json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

                return {
                    "task_id": task_id,
                    "question": case["question"],
                    "predicted_label": ev["predicted_label"],
                    "predicted_text": ev["predicted_text"],
                    "correct_label": ev["correct_label"],
                    "correct_text": case.get("correct_text", ""),
                    "theorem_type": case.get("theorem_type", []),
                    "hard": hard,
                    "agent": "ok",
                    "usage": usage,
                }
            except Exception as e:
                last_error = e
                es = str(e)
                is_rate = "429" in es or "Throttling" in es or "rate" in es.lower()
                                                                
                if retry < max_retries:
                    await asyncio.sleep((10 if is_rate else 5) * (retry + 1))
                    continue
                print(f"  [{index}/{total}] {task_id}:  error - {type(e).__name__}: {e}", flush=True)
                break

        return {
            "task_id": task_id,
            "question": case["question"],
            "predicted_label": "",
            "predicted_text": "",
            "correct_label": normalize_label(correct_label),
            "correct_text": case.get("correct_text", ""),
            "theorem_type": case.get("theorem_type", []),
            "hard": 0,
            "agent": "error",
            "error": str(last_error) if last_error else "Unknown",
        }

async def run_evaluation(args):
    print("=" * 70)
    print("LiveMathematicianBench theorem multiple-choice solving - evaluation")
    print("=" * 70)

    if args.model:
        MODEL_CONFIG["model_name"] = args.model
    MODEL_CONFIG["model_name"] = provider_model(MODEL_CONFIG["model_name"])
    
                       
    if args.backend == "anthropic":
        MODEL_CONFIG["backend"] = "anthropic"
        MODEL_CONFIG["api_key_env"] = "ANTHROPIC_API_KEY"
        MODEL_CONFIG["base_url"] = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("environment variable ANTHROPIC_API_KEY not set")
            sys.exit(1)
        print(f"\n model: anthropic / {MODEL_CONFIG['model_name']}")
    else:
        api_key = openai_compatible_api_key(MODEL_CONFIG["api_key_env"])
        print(f"\n model: {openai_compatible_provider_label()} / {MODEL_CONFIG['model_name']}")

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

    test_cases = []
    with open(args.data, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                test_cases.append(json.loads(line))
    if args.filter_ids:
        test_cases = [c for c in test_cases if c["task_id"] in args.filter_ids]
    if args.limit > 0:
        test_cases = test_cases[:args.limit]
    print(f"data: {len(test_cases)} cases from {args.data}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output_base) if args.output_base else (
        Path(__file__).parent.parent / "evolved" / "livemath-solver")
    if not output_base.is_absolute():
        output_base = Path(__file__).parent.parent / output_base
    dataset_name = Path(args.data).stem
    run_dir = output_base / f"{dataset_name}_run_{timestamp}"
    evals_dir = run_dir / "evals"
    traces_dir = run_dir / "traces"
    evals_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    print(f"output: {run_dir}")
    print(f"concurrency: {args.max_concurrent}")

    import httpx
    semaphore = asyncio.Semaphore(args.max_concurrent)
    start_time = time.time()
                                                                  
    limits = httpx.Limits(max_connections=args.max_concurrent,
                          max_keepalive_connections=args.max_concurrent)
    async with httpx.AsyncClient(timeout=600.0, limits=limits) as client:
        tasks = [
            evaluate_case_with_timeout(c, system_prompt, semaphore, api_key, traces_dir,
                          i + 1, len(test_cases), client, timeout=3600.0)              
            for i, c in enumerate(test_cases)
        ]
        results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    total = len(results)
    error_count = sum(1 for r in results if r["agent"] in ["error", "timeout"])
    timeout_count = sum(1 for r in results if r["agent"] == "timeout")
    hard_count = sum(r["hard"] for r in results)
    accuracy = hard_count / total * 100 if total else 0

                          
    type_stats: dict = {}
    for r in results:
        for t in (r.get("theorem_type") or ["(none)"]):
            type_stats.setdefault(t, [0, 0])
            type_stats[t][1] += 1
            type_stats[t][0] += r["hard"]

    print(f"\n  elapsed: {elapsed:.1f}s ({elapsed/max(total,1):.2f}s/case)")
    print(f"\n{'='*70}")
    print(f"evaluation results:")
    print(f"{'='*70}")
    print(f"  total case  count: {total}")
    print(f"  execution exception: {error_count}")
    if timeout_count > 0:
        print(f"  └─ timeout: {timeout_count}")
    print(f"  ──────────────────────")
    print(f"  accuracy (EM) : {accuracy:.1f}% ({hard_count}/{total})")
    print(f"\n  accuracy grouped by theorem type:")
    for t in sorted(type_stats, key=lambda x: -type_stats[x][1]):
        c, n = type_stats[t]
        print(f"    {t}: {c}/{n} ({c/n*100:.0f}%)")

    wrong = [r for r in results if not r["hard"] and r["agent"] != "error"]
    if wrong:
        print(f"\n wrong case ({len(wrong)} ):")
        for w in wrong:
            print(f"  {w['task_id']}: pred={w['predicted_label']} gold={w['correct_label']} "
                  f"types={w.get('theorem_type')}")

    result_file = evals_dir / f"results_{dataset_name}_{timestamp}.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": f"{('anthropic' if MODEL_CONFIG.get('backend') == 'anthropic' else openai_compatible_provider_label())}/{MODEL_CONFIG['model_name']}",
        "skill_path": str(skill_path),
        "data_path": str(args.data),
        "total": total,
        "error_count": error_count,
        "hard_count": hard_count,
        "accuracy": round(accuracy, 2),
        "type_accuracy": {t: round(type_stats[t][0] / type_stats[t][1] * 100, 1)
                          for t in type_stats},
        "wrong_ids": [w["task_id"] for w in wrong],
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
    parser = argparse.ArgumentParser(description="LiveMath theorem multiple-choice solving - batchevaluation")
    parser.add_argument("--data", "-d", required=True, help="datasetpath (.jsonl) ")
    parser.add_argument("--skill", "-s", required=True, help="Skill directorypath")
    parser.add_argument("--filter-ids", "-f", nargs="*", default=[], dest="filter_ids",
                        help="only evaluationspecified  task_id")
    parser.add_argument("--limit", "-l", type=int, default=0, help="only test top  N  items (0=full ) ")
    parser.add_argument("--max-concurrent", "-c", type=int, default=12, dest="max_concurrent",
                        help="concurrencytask count (default 12, prevent  429) ")
    parser.add_argument("--output-base", "-o", default="", dest="output_base",
                        help="resultsoutputdirectory (default evolved/livemath-solver) ")
    parser.add_argument("--model", "-m", default="", dest="model",
                        help="coveragebackbonemodelname (like  qwen3.7-max, default qwen3.6-plus) ")
    parser.add_argument("--backend", choices=["openai_compatible", "anthropic"], default="openai_compatible",
                        help="LLM backend: openai_compatible (OpenAI-compatible/qwen)  or  anthropic (Anthropic Messages API) ")
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
