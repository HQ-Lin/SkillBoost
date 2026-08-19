#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import re
import subprocess
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent

                                                         
           
                                                         
SYSTEM_PROMPT_TEMPLATE = """\
You are an expert software engineer that resolves GitHub issues by producing a code patch.

{skill_content}

You will be given a GitHub issue with hints and repository information.
Produce a patch in unified diff format (git diff style) that fixes the issue.
Output ONLY the raw unified diff. Do not include explanations or markdown fences."""

USER_PROMPT_TEMPLATE = """\
## GitHub Issue

{problem_statement}

{hints_text}

repo: {repo}
benchmarkversion: {version}

generate fix this  Issue  patch. output pure  unified diff format, not require with any other text. """

                                                         
               
                                                         
def load_skill(skill_path: Path) -> str:
    """read SKILL.md,  YAML frontmatter, returned body as  system_prompt injectcontent.

    --skill supportdirect SKILL.md file, also supportat directory.
    """
    if skill_path.is_dir():
        skill_path = skill_path / "SKILL.md"
    if not skill_path.exists():
        print(f"Skill file not found: {skill_path}")
        sys.exit(1)
    content = skill_path.read_text(encoding="utf-8")
                                    
    if content.lstrip().startswith("---"):
        stripped = content.lstrip()
        end_idx = stripped.find("---", 3)
        if end_idx != -1:
            content = stripped[end_idx + 3:].strip()
    return content

def load_dataset(data_path: Path) -> list:
    cases = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases

                                                         
      
                                                         
def extract_patch(text: str) -> str:
    """from modeloutput in extract unified diff.

    preferextract markdown code (```diff / ```patch / ``` wrap)  in  content,
    whether then returned removefirst emptyafter  . no parsethen returned emptycharsstring.
    """
    if not text:
        return ""
                                                         
    fence = re.search(r"```(?:diff|patch)?\s*\n(.*?)```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        candidate = text
    candidate = candidate.strip()
                                                     
    if not candidate:
        return ""
    if ("diff --git" in candidate or "--- " in candidate
            or "+++ " in candidate or candidate.startswith("Index:")):
                             
        return candidate if candidate.endswith("\n") else candidate + "\n"
    return ""

                                                         
             
                                                         
                                             
_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$")

def fix_hunk_counts(patch: str) -> str:
    """ unified diff  in  hunk header  line countcount count.

    modelgenerate  `@@ -s,c +s,c @@`  in line count c  and actual linesnot consistent,  git apply
    failed. function countper  linesscan, for per  hunk by actual lines old_count / new_count:
      - old_count = context lines(emptystarts with a space) + delete lines(- start)
      - new_count = context lines(emptystarts with a space) + added lines(+ start)
    keepraw  start line  and  header after  function countnamecommentnot change.

    boundary: patch as empty or not with  `@@` returned ；multi- hunk / multi-fileeach independent.
    """
    if not patch or "@@" not in patch:
        return patch

    lines = patch.split("\n")
    out = []
    i = 0
    n = len(lines)
    while i < n:
        m = _HUNK_HEADER_RE.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        old_start, new_start, trailing = m.group(1), m.group(2), m.group(3)
                                             
        body = []
        j = i + 1
        while j < n:
            bl = lines[j]
            if (bl.startswith("@@") or bl.startswith("--- ")
                    or bl.startswith("+++ ") or bl.startswith("diff --git")
                    or bl.startswith("Index:")):
                break
            body.append(bl)
            j += 1
        old_count = 0
        new_count = 0
        for bl in body:
            if bl.startswith("-"):
                old_count += 1
            elif bl.startswith("+"):
                new_count += 1
            elif bl.startswith(" "):
                old_count += 1
                new_count += 1
                                                    
        out.append(f"@@ -{old_start},{old_count} +{new_start},{new_count} @@{trailing}")
        out.extend(body)
        i = j
    return "\n".join(out)

                                                         
                          
                                                         
async def call_llm_api(messages: list, api_key: str, timeout: float = 300.0) -> dict:
    """call OpenAI-compatible compatible-mode, returned full choices[0].message + usage. """
    import httpx
    payload = {
        "model": MODEL_CONFIG["model_name"],
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 8192,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = await async_chat_completion(client, payload, api_key=api_key)
        return {
            "content": data["choices"][0]["message"].get("content") or "",
            "usage": data.get("usage", {}),
        }

                                                         
         
                                                         
async def generate_patch(case: dict, system_prompt: str, semaphore: asyncio.Semaphore,
                         api_key: str, traces_dir: Path, index: int, total: int) -> dict:
    async with semaphore:
        instance_id = case["instance_id"]
        user_prompt = USER_PROMPT_TEMPLATE.format(
            problem_statement=case.get("problem_statement", ""),
            hints_text=case.get("hints_text", "") or " (no ) ",
            repo=case.get("repo", ""),
            version=case.get("version", ""),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        max_retries = 3
        last_error = None
        retried = 0
        t0 = time.time()
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    retried = attempt
                result = await call_llm_api(messages, api_key)
                response_text = result["content"]
                patch = extract_patch(response_text)
                patch = fix_hunk_counts(patch)                         
                elapsed = time.time() - t0
                usage = result.get("usage", {})
                icon = ""if patch else "⬜"
                print(f"  [{index}/{total}] {instance_id}: patch={'has ' if patch else 'empty'} "
                      f"{icon} ({elapsed:.1f}s, retry={retried})", flush=True)

                trace = {
                    "instance_id": instance_id,
                    "repo": case.get("repo", ""),
                    "version": case.get("version", ""),
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "response": response_text,
                    "patch": patch,
                    "usage": usage,
                    "elapsed_seconds": round(elapsed, 2),
                    "retried": retried,
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
                    "_retried": retried,
                    "_usage": usage,
                    "_empty": not bool(patch),
                    "_error": None,
                }
            except Exception as e:                
                last_error = e
                es = str(e)
                if "429" in es or "Throttling" in es or "rate" in es.lower():
                    await asyncio.sleep(min(2 ** (attempt + 1), 30))
                    continue
                                 
                await asyncio.sleep(2 * (attempt + 1))
                continue

        elapsed = time.time() - t0
        print(f"  [{index}/{total}] {instance_id}:  generate failed - {last_error}", flush=True)
        trace = {
            "instance_id": instance_id,
            "repo": case.get("repo", ""),
            "version": case.get("version", ""),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response": "",
            "patch": "",
            "usage": {},
            "elapsed_seconds": round(elapsed, 2),
            "retried": max_retries,
            "eval_result": None,
            "error": str(last_error),
            "timestamp": datetime.now().isoformat(),
        }
        (traces_dir / f"trace_{instance_id}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "instance_id": instance_id,
            "model_name_or_path": MODEL_CONFIG["model_name"],
            "model_patch": "",
            "_elapsed": round(elapsed, 2),
            "_retried": max_retries,
            "_usage": {},
            "_empty": True,
            "_error": str(last_error),
        }

                                                         
                       
                                                         
def load_existing_predictions(predictions_file: Path) -> dict:
    existing = {}
    if predictions_file.exists():
        with open(predictions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    existing[obj["instance_id"]] = obj
                except (json.JSONDecodeError, KeyError):
                    continue
    return existing

                                                         
                   
                                                         
def run_swebench_eval(predictions_file: Path, dataset_path: Path, run_id: str,
                      max_workers: int) -> Path:
    """sub processescall swebench.harness.run_evaluation, returned final  report filepath.

    make_run_report at  cwd write out `{model__name}.{run_id}.json`.
    """
    cmd = [
        sys.executable, "-m", "swebench.harness.run_evaluation",
        "--dataset_name", str(dataset_path),
        "--predictions_path", str(predictions_file),
        "--run_id", run_id,
        "--max_workers", str(max_workers),
        "--namespace", "",
    ]
    print("\n call SWE-bench evaluation harness:")
    print("   " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if proc.returncode != 0:
        print(f"SWE-bench evaluationsubprocess returned non-zero exit code: {proc.returncode}")

                                                                          
    model_tag = MODEL_CONFIG["model_name"].replace("/", "__")
    report_file = PROJECT_ROOT / f"{model_tag}.{run_id}.json"
    return report_file

def parse_per_instance_status(run_id: str, instance_ids: list) -> dict:
    """readper  example  report.json, returned  {instance_id: {resolved, tests_status}}. """
    model_tag = MODEL_CONFIG["model_name"].replace("/", "__")
    log_dir = PROJECT_ROOT / "logs" / "run_evaluation" / run_id / model_tag
    status = {}
    for iid in instance_ids:
        report_path = log_dir / iid / "report.json"
        if not report_path.exists():
            continue
        try:
            content = report_path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            data = json.loads(content)
            entry = data.get(iid, {})
            status[iid] = {
                "resolved": bool(entry.get("resolved", False)),
                "tests_status": entry.get("tests_status"),
            }
        except (json.JSONDecodeError, KeyError):
            continue
    return status

                                                         
        
                                                         
def build_results(cases: list, predictions: dict, final_report: dict,
                  per_instance: dict) -> tuple:
    """generate per example results columntable + summary report dict. """
    resolved_ids = set(final_report.get("resolved_ids", []))
    empty_patch_ids = set(final_report.get("empty_patch_ids", []))
    error_ids = set(final_report.get("error_ids", []))

    results = []
    per_repo = {}                             
    for case in cases:
        iid = case["instance_id"]
        repo = case.get("repo", "")
        pred = predictions.get(iid, {})
        patch = pred.get("model_patch", "")

        if iid in resolved_ids:
            st, reason = "resolved", "tests passed"
        elif iid in empty_patch_ids or not patch:
            st, reason = "error", "empty patch"
        elif iid in error_ids:
            st, reason = "error", "evaluation error"
        else:
            st, reason = "failed", "tests failed"
        if pred.get("_error"):
            st, reason = "error", f"generation error: {pred['_error']}"

        per_repo.setdefault(repo, [0, 0])
        per_repo[repo][1] += 1
        if st == "resolved":
            per_repo[repo][0] += 1

        results.append({
            "instance_id": iid,
            "repo": repo,
            "status": st,
            "reason": reason,
            "empty_patch": not bool(patch),
            "tests_status": per_instance.get(iid, {}).get("tests_status"),
        })

    total = len(cases)
    resolved = sum(1 for r in results if r["status"] == "resolved")
    failed = sum(1 for r in results if r["status"] == "failed")
    errored = sum(1 for r in results if r["status"] == "error")

    report = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL_CONFIG["model_name"],
        "total": total,
        "resolved": resolved,
        "failed": failed,
        "error": errored,
        "resolved_rate": round(resolved / total * 100, 2) if total else 0.0,
        "per_repo_accuracy": {
            repo: {
                "resolved": v[0],
                "total": v[1],
                "rate": round(v[0] / v[1] * 100, 2) if v[1] else 0.0,
            }
            for repo, v in sorted(per_repo.items())
        },
        "swebench_report": final_report or None,
    }
    return results, report

                                                         
     
                                                         
async def run(args):
    print("=" * 70)
    print("SWE-bench evaluation Harness")
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
    print(f"output directory: {output_dir}")
    print(f"concurrency: {args.concurrency}  |  evaluation workers: {args.max_workers}")

                                                 
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
            generate_patch(c, system_prompt, semaphore, api_key, traces_dir,
                           i + 1, len(pending))
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
    report["skill_path"] = str(args.skill)
    report["dataset_path"] = str(args.dataset)
    report["gen_elapsed_seconds"] = round(elapsed, 1)

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
    print("  by repository:")
    for repo, v in report["per_repo_accuracy"].items():
        print(f"    {repo}: {v['resolved']}/{v['total']} ({v['rate']}%)")
    print(f"\n report: {report_out}")
    print(f"per-instance results: {results_file}")
    print(f"traces: {traces_dir}")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="SWE-bench evaluation Harness")
    parser.add_argument("--skill", required=True, help="SKILL.md filepath ( or at directory) ")
    parser.add_argument("--dataset", required=True, help="datasetpath (.jsonl) ")
    parser.add_argument("--concurrency", type=int, default=10, help="concurrencygenerate  (default 10, cap 20) ")
    parser.add_argument("--max_workers", type=int, default=4, help="SWE-bench evaluationparallel worker  count")
    parser.add_argument("--run_id", required=True, help=" timesevaluation run_id (SWE-bench harness use ) ")
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
