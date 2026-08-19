#!/usr/bin/env python3
import argparse
import ast
import asyncio
import base64
import json
import mimetypes
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
You are an expert visual document question answering agent.

{skill_content}

You will receive a document image and a question about the document.
Read the visual evidence carefully and answer concisely.
Return the final answer inside <answer>...</answer>."""

USER_TEXT_TEMPLATE = "{question}\n\nReturn the final answer inside <answer>...</answer>."

                                                         
                                    
                                                         
ANLS_THRESHOLD = 0.5

def _normalize_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def _score_one(pred, target, threshold=ANLS_THRESHOLD) -> float:
    p, t = _normalize_text(pred), _normalize_text(target)
    if not p and not t:
        return 1.0
    if not p or not t:
        return 0.0
    nd = _levenshtein(p, t) / max(len(p), len(t))
    return 0.0 if nd >= threshold else 1.0 - nd

def extract_answer(text: str) -> str:
    lower = text.lower()
    start = lower.rfind("<answer>")
    end = lower.rfind("</answer>")
    if start != -1 and end != -1 and end > start:
        return text[start + len("<answer>"):end].strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[-1] if lines else text.strip()

def anls_evaluate(prediction_text: str, gold_answers: list) -> dict:
    answer = extract_answer(prediction_text)
    score = 0.0
    for tgt in (gold_answers or [""]):
        score = max(score, _score_one(answer, tgt))
    return {"anls": score, "predicted_answer": answer}

                                                         
        
                                                         
def _data_uri(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b}"

async def call_llm_api(messages: list, api_key: str) -> tuple:
    import httpx
    payload = {
        "model": MODEL_CONFIG["model_name"],
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return content, usage

                                                         
       
                                                         
async def evaluate_case(case, system_prompt, semaphore, api_key, traces_dir, index, total):
    async with semaphore:
        task_id = case["task_id"]
        gold = case.get("answers", [])
        user_text = USER_TEXT_TEMPLATE.format(question=case["question"])
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": _data_uri(case["image_path"])}},
            ]},
        ]

        max_retries = 2
        last_error = None
        for retry in range(max_retries + 1):
            try:
                if retry > 0:
                    await asyncio.sleep(3 * retry)
                response_text, usage = await call_llm_api(messages, api_key)
                ev = anls_evaluate(response_text, gold)
                anls = ev["anls"]
                hard = int(anls >= 0.999)
                icon = ""if hard else (""if anls >= 0.5 else "")
                print(f"  [{index}/{total}] {task_id}: pred='{ev['predicted_answer'][:30]}' "
                      f"gold={gold} ANLS={anls:.3f} {icon}")

                trace = {
                    "task_id": task_id,
                    "question": case["question"],
                    "image_path": case["image_path"],
                    "response": response_text,
                    "predicted_answer": ev["predicted_answer"],
                    "gold_answers": gold,
                    "anls": anls,
                    "hard": hard,
                    "usage": usage,
                    "timestamp": datetime.now().isoformat(),
                }
                (traces_dir / f"trace_{task_id}.json").write_text(
                    json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

                return {
                    "task_id": task_id,
                    "question": case["question"],
                    "predicted_answer": ev["predicted_answer"],
                    "gold_answers": gold,
                    "anls": anls,
                    "hard": hard,
                    "agent": "ok",
                }
            except Exception as e:
                last_error = e
                es = str(e)
                if "429" in es or "Throttling" in es or "rate" in es.lower():
                    await asyncio.sleep(10 * (retry + 1))
                    continue
                print(f"  [{index}/{total}] {task_id}:  error - {e}")
                break

        return {
            "task_id": task_id,
            "question": case["question"],
            "predicted_answer": "",
            "gold_answers": gold,
            "anls": 0.0,
            "hard": 0,
            "agent": "error",
            "error": str(last_error) if last_error else "Unknown",
        }

async def run_evaluation(args):
    print("=" * 70)
    print("DocVQA document VQA - evaluation")
    print("=" * 70)

    MODEL_CONFIG["model_name"] = provider_model(MODEL_CONFIG["model_name"])
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
        Path(__file__).parent.parent / "evolved" / "docvqa-solver")
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
    start_time = time.time()
    tasks = [
        evaluate_case(c, system_prompt, semaphore, api_key, traces_dir, i + 1, len(test_cases))
        for i, c in enumerate(test_cases)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    total = len(results)
    error_count = sum(1 for r in results if r["agent"] == "error")
    hard_count = sum(r["hard"] for r in results)
                                                      
    fail_ids = [r["task_id"] for r in results if not r["hard"] and r["agent"] != "error"]
    anls_sum = sum(r["anls"] for r in results)
    soft05 = sum(1 for r in results if r["anls"] >= 0.5)
    hard_acc = hard_count / total * 100 if total else 0
    mean_anls = anls_sum / total if total else 0
    soft_rate = soft05 / total * 100 if total else 0

    print(f"\n  elapsed: {elapsed:.1f}s ({elapsed/max(total,1):.2f}s/case)")
    print(f"\n{'='*70}")
    print(f"evaluation results:")
    print(f"{'='*70}")
    print(f"  total case  count: {total}")
    print(f"  execution exception: {error_count}")
    print(f"  ──────────────────────")
    print(f"  Hard accuracy (donefull hit ANLS>=0.999) : {hard_acc:.1f}% ({hard_count}/{total})")
    print(f"  avg ANLS: {mean_anls:.4f}")
    print(f"  soft hit rate (ANLS>=0.5) : {soft_rate:.1f}% ({soft05}/{total})")

    wrong = [r for r in results if not r["hard"] and r["agent"] != "error"]
    if wrong:
        print(f"\n incompletefull hit case ({len(wrong)}  , showing at most  25) :")
        for w in wrong[:25]:
            print(f"  {w['task_id']}: Q='{w['question'][:45]}' "
                  f"pred='{w['predicted_answer'][:25]}' gold={w['gold_answers']} ANLS={w['anls']:.2f}")

    result_file = evals_dir / f"results_{dataset_name}_{timestamp}.jsonl"
    with open(result_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": f"{openai_compatible_provider_label()}/{MODEL_CONFIG['model_name']}",
        "skill_path": str(skill_path),
        "data_path": str(args.data),
        "total": total,
        "error_count": error_count,
        "hard_count": hard_count,
        "hard_accuracy": round(hard_acc, 2),
        "mean_anls": round(mean_anls, 4),
        "soft_hit_count": soft05,
        "soft_hit_rate": round(soft_rate, 2),
        "fail_ids": fail_ids,
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
    parser = argparse.ArgumentParser(description="DocVQA document VQA - batchevaluation")
    parser.add_argument("--data", "-d", required=True, help="datasetpath (.jsonl) ")
    parser.add_argument("--skill", "-s", required=True, help="Skill directorypath")
    parser.add_argument("--filter-ids", "-f", nargs="*", default=[], dest="filter_ids",
                        help="only evaluationspecified  task_id")
    parser.add_argument("--limit", "-l", type=int, default=0, help="only test top  N  items (0=full ) ")
    parser.add_argument("--max-concurrent", "-c", type=int, default=12, dest="max_concurrent",
                        help="concurrencytask count (default 12, prevent  429) ")
    parser.add_argument("--output-base", "-o", default="", dest="output_base",
                        help="resultsoutputdirectory (default evolved/docvqa-solver) ")
    parser.add_argument("--model", "-m", default="", dest="model",
                        help="coveragebackbonemodelname (like  qwen3.7-max, default qwen3.6-plus) ")
    args = parser.parse_args()

    if args.model:
        MODEL_CONFIG["model_name"] = args.model

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
