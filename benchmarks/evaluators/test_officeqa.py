#!/usr/bin/env python3
import asyncio
import json
import math
import os
import re
import string
import sys
import argparse
import time
from collections import Counter
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
    "model_name": "qwen3.6-plus",
    "api_key_env": "LLM_API_KEY",
}

ACTIVE_MODEL_CONFIG = MODEL_CONFIG_GENERIC

                                                         
        
                                                         

SYSTEM_PROMPT_TEMPLATE = """\
you  is one namedocument countvalue QAexpert. you  task is  official documentsnippet (Treasury Bulletin / Federal Reserve Bulletin  etc) answeruse  countvalue/compute/compareclassquestions.

strictwith answer format rules:

{skill_content}
"""

USER_PROMPT_TEMPLATE = """\
base at "official documentsnippet"answerquestions. only given evidence linesextract and compute, forbiddenuse model missing.

【questions】
{question}

【official documentsnippet ( as you retrieval  oracle evidence) 】
{context}

only output JSON (not require any  markdown wrap, not require multi-extra text) :
{{"answer": "final  countvalue or columntable", "reason": "one-sentence evidence/computenote (≤120 ) "}}"""

                                                         
     
                                                         

async def call_llm_api(messages: list, model_name: str, api_key: str) -> str:
    import httpx
    payload = {"model": model_name, "messages": messages, "temperature": 0.1, "max_tokens": 2048}
    async with httpx.AsyncClient(timeout=180.0) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        return data["choices"][0]["message"]["content"]

async def call_llm(messages: list, config: dict) -> str:
    api_key = openai_compatible_api_key(config["api_key_env"])
    return await call_llm_api(messages, config["model_name"], api_key)

                                                         
         
                                                         

_NUMERIC_CHARS = set("0123456789.-")

def parse_answer(response_text: str) -> str:
    """from  LLM output in extract answer field. """
                        
    m = re.search(r'\{[^{}]*"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text, re.DOTALL)
    if m:
        return m.group(1).replace('\\"', '"').replace("\\n", " ").strip()
                                 
    m2 = re.search(r'"answer"\s*:\s*([\-+]?\d[\d,\.]*)', response_text)
    if m2:
        return m2.group(1).strip()
    return response_text.strip()

def parse_reason(response_text: str) -> str:
    m = re.search(r'"reason"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text)
    if m:
        reason = m.group(1).replace('\\"', '"').replace("\\n", " ")
        return reason[:240]
    return ""

def normalize_answer(text: str) -> str:
    """Answer normalization (lowercase, punctuation, digits, units)."""
    text = str(text).lower().strip()
    text = text.replace(",", "")
    text = "".join(ch for ch in text if ch not in string.punctuation or ch in _NUMERIC_CHARS or ch == "%")
    text = re.sub(
        r"\b(million|millions|billion|billions|thousand|thousands|dollars|dollar|usd|nominal|percent|percentage|points)\b",
        " ",
        text,
    )
    text = " ".join(text.split())
    return text

def exact_match(pred: str, gold: str) -> float:
    return 1.0 if normalize_answer(pred) == normalize_answer(gold) else 0.0

def sub_em(pred: str, gold: str) -> float:
    p, g = normalize_answer(pred), normalize_answer(gold)
    if not p or not g:
        return 0.0
    return 1.0 if (p in g or g in p) else 0.0

def token_f1(pred: str, gold: str) -> float:
    p = normalize_answer(pred).split()
    g = normalize_answer(gold).split()
    if not p or not g:
        return 1.0 if p == g else 0.0
    common = Counter(p) & Counter(g)
    n = sum(common.values())
    if n == 0:
        return 0.0
    precision = n / len(p)
    recall = n / len(g)
    return 2 * precision * recall / (precision + recall)

def _to_float(s: str):
    s = str(s).strip().replace(",", "").replace("$", "").replace("%", "")
    s = re.sub(r"\b(million|millions|billion|billions|thousand|thousands|dollars|dollar|usd|percent|percentage|points)\b", "", s, flags=re.I)
    s = s.strip()
    try:
        return float(s)
    except Exception:
        return None

def num_em(pred: str, gold: str, atol: float = 1e-6, rtol: float = 1e-3) -> float:
    pv, gv = _to_float(pred), _to_float(gold)
    if pv is None or gv is None:
        return 0.0
    if math.isnan(pv) or math.isnan(gv):
        return 0.0
    diff = abs(pv - gv)
    if diff <= atol:
        return 1.0
    denom = max(abs(gv), 1e-9)
    if diff / denom <= rtol:
        return 1.0
    return 0.0

def case_correct(pred: str, gold: str) -> bool:
    """: EM  or  countvalue EM one  as correct (consistent with the reference implementation). """
    return exact_match(pred, gold) == 1.0 or num_em(pred, gold) == 1.0

                                                         
    
                                                         

async def evaluate_case(case: dict, system_prompt: str, semaphore: asyncio.Semaphore,
                        model_config: dict, traces_dir: Path, index: int, total: int) -> dict:
    async with semaphore:
        task_id = case["task_id"]
        user_prompt = USER_PROMPT_TEMPLATE.format(question=case["question"], context=case["context"])
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        gold = str(case["gold_answer"])

        max_retries = 2
        last_error = None
        for retry in range(max_retries + 1):
            try:
                if retry > 0:
                    await asyncio.sleep(3 * retry)
                response_text = await call_llm(messages, model_config)
                pred = parse_answer(response_text)
                reason = parse_reason(response_text)

                em = exact_match(pred, gold)
                f1 = token_f1(pred, gold)
                sem_ = sub_em(pred, gold)
                nem = num_em(pred, gold)
                correct = (em == 1.0) or (nem == 1.0)

                icon = ""if correct else ""
                print(f"  [{index}/{total}] {task_id}: pred='{pred[:40]}' gold='{gold[:40]}' EM={em:.0f} F1={f1:.2f} {icon}")

                trace = {
                    "task_id": task_id,
                    "question": case["question"],
                    "gold": gold,
                    "predicted": pred,
                    "em": em, "f1": f1, "sub_em": sem_, "num_em": nem,
                    "correct": correct,
                    "reason": reason,
                    "response": response_text,
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
                    "difficulty": case.get("difficulty", ""),
                    "trace_file": str(trace_file),
                }

            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "Throttling" in error_str or "rate" in error_str.lower():
                    wait_time = 10 * (retry + 1)
                    print(f"  [{index}/{total}] {task_id}: rate limit, wait  {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                print(f"  [{index}/{total}] {task_id}:  {e}")
                break

        return {
            "task_id": task_id,
            "question": case["question"],
            "gold": gold,
            "predicted": "",
            "em": 0.0, "f1": 0.0, "sub_em": 0.0, "num_em": 0.0,
            "correct": False,
            "reason": "",
            "error": str(last_error) if last_error else "Unknown error",
            "difficulty": case.get("difficulty", ""),
            "trace_file": None,
        }

async def run_evaluation(args):
    print("=" * 70)
    print("OfficeQA document countvalue QA - evaluation")
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
        print(f"   after filtering {len(test_cases)} cases")

    print(f"data: {len(test_cases)} cases from {jsonl_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output_base) if args.output_base else Path(__file__).parent.parent / "evolved" / "officeqa-solver"
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

    semaphore = asyncio.Semaphore(args.max_concurrent)
    start = time.time()
    tasks = [
        evaluate_case(c, system_prompt, semaphore, model_config, traces_dir, i + 1, len(test_cases))
        for i, c in enumerate(test_cases)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    print(f"\n  elapsed: {elapsed:.1f}s")

        
    total = len(results)
    err = sum(1 for r in results if "error" in r and r.get("error"))
    em_sum = sum(r["em"] for r in results)
    f1_sum = sum(r["f1"] for r in results)
    sub_em_sum = sum(r["sub_em"] for r in results)
    num_em_sum = sum(r["num_em"] for r in results)
    correct = sum(1 for r in results if r["correct"])

    em_mean = em_sum / total * 100 if total else 0
    f1_mean = f1_sum / total * 100 if total else 0
    sub_em_mean = sub_em_sum / total * 100 if total else 0
    num_em_mean = num_em_sum / total * 100 if total else 0
    acc = correct / total * 100 if total else 0

    print(f"\n{'='*70}")
    print(f"evaluation results")
    print(f"{'='*70}")
    print(f"  total case: {total}, execution exception: {err}")
    print(f"  Accuracy (EM ∨ NumEM): {acc:.2f}% ({correct}/{total})")
    print(f"  EM:     {em_mean:.2f}%")
    print(f"  F1:     {f1_mean:.2f}%")
    print(f"  Sub-EM: {sub_em_mean:.2f}%")
    print(f"  Num-EM: {num_em_mean:.2f}%")

          
    diffs = sorted(set(r.get("difficulty", "") for r in results))
    for d in diffs:
        if not d:
            continue
        sub = [r for r in results if r.get("difficulty") == d]
        if not sub:
            continue
        sub_acc = sum(1 for r in sub if r["correct"]) / len(sub) * 100
        sub_em_local = sum(r["em"] for r in sub) / len(sub) * 100
        sub_f1 = sum(r["f1"] for r in sub) / len(sub) * 100
        print(f"  [{d}] n={len(sub)} Acc={sub_acc:.2f}% EM={sub_em_local:.2f}% F1={sub_f1:.2f}%")

             
    wrong = [r for r in results if not r["correct"]]
    if wrong:
        print(f"\n failed case ({len(wrong)}  total, showing first  20):")
        for w in wrong[:20]:
            print(f"  {w['task_id']}: gold='{w['gold'][:40]}' pred='{w['predicted'][:40]}' | {w['reason'][:80]}")

          
    result_file = evals_dir / f"results_{dataset_name}_{timestamp}.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "run_timestamp": timestamp,
        "model": f"{model_config['model_provider']}/{model_config['model_name']}",
        "skill_path": str(skill_path),
        "data_path": str(jsonl_path),
        "total": total,
        "error_count": err,
        "accuracy": round(acc, 2),
        "em": round(em_mean, 2),
        "f1": round(f1_mean, 2),
        "sub_em": round(sub_em_mean, 2),
        "num_em": round(num_em_mean, 2),
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
    parser = argparse.ArgumentParser(description="OfficeQA document countvalue QA - batchevaluation")
    parser.add_argument("--data", "-d", required=True, help="datasetpath (.jsonl) ")
    parser.add_argument("--skill", "-s", required=True, help="Skill directorypath")
    parser.add_argument("--filter-ids", "-f", nargs="*", default=[], dest="filter_ids", help="only evaluationspecified  task_id")
    parser.add_argument("--max-concurrent", "-c", type=int, default=10, dest="max_concurrent", help="concurrency (default 10) ")
    parser.add_argument("--output-base", "-o", default="", dest="output_base", help="resultsoutputdirectory")
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
