#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "swebench"

                
PREFERRED_REPOS = [
    "django/django",
    "sympy/sympy",
    "psf/requests",
    "pallets/flask",
    "matplotlib/matplotlib",
    "scikit-learn/scikit-learn",
    "sphinx-doc/sphinx",
    "pytest-dev/pytest",
    "astropy/astropy",
    "pydata/xarray",
]

            
OUTPUT_FIELDS = [
    "instance_id",
    "repo",
    "version",
    "base_commit",
    "problem_statement",
    "hints_text",
    "patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "created_at",
]

def patch_line_count(patch: str) -> int:
    """stats gold patch  in actualadded/delete codeline count (not with  diff ) . """
    if not patch:
        return 0
    count = 0
    for line in patch.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            count += 1
    return count

def _as_list(value):
    """FAIL_TO_PASS / PASS_TO_PASS at raw datacan can  is  JSON charsstring or  list. """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [value]
        except json.JSONDecodeError:
            return [value]
    return list(value)

def normalize_record(row: dict) -> dict:
    """from raw data linesbuildunifiedoutputformat. """
    return {
        "instance_id": row.get("instance_id", ""),
        "repo": row.get("repo", ""),
        "version": str(row.get("version", "")),
        "base_commit": row.get("base_commit", ""),
        "problem_statement": row.get("problem_statement", "") or "",
        "hints_text": row.get("hints_text", "") or "",
        "patch": row.get("patch", "") or "",
        "test_patch": row.get("test_patch", "") or "",
        "FAIL_TO_PASS": _as_list(row.get("FAIL_TO_PASS")),
        "PASS_TO_PASS": _as_list(row.get("PASS_TO_PASS")),
        "created_at": str(row.get("created_at", "")),
    }

def select_train(records: list, train_size: int, per_repo: int,
                 max_patch_lines: int, min_ps: int, max_ps: int) -> list:
    """select by strategy train samples. """
                                               
    eligible = []
    for r in records:
        plen = patch_line_count(r["patch"])
        pslen = len(r["problem_statement"])
        if plen == 0 or plen > max_patch_lines:
            continue
        if pslen < min_ps or pslen > max_ps:
            continue
        eligible.append((plen, r))

                                                  
    by_repo = {}
    for plen, r in eligible:
        repo = r["repo"]
        if repo not in PREFERRED_REPOS:
            continue
        by_repo.setdefault(repo, []).append((plen, r))
    for repo in by_repo:
        by_repo[repo].sort(key=lambda x: (x[0], x[1]["instance_id"]))

                                            
                                                  
    selected = []
    repos_in_order = [r for r in PREFERRED_REPOS if r in by_repo]
    for repo in repos_in_order:
        if len(selected) >= train_size:
            break
        for plen, r in by_repo[repo][:per_repo]:
            if len(selected) >= train_size:
                break
            selected.append(r)

                               
    if len(selected) < train_size:
        chosen_ids = {r["instance_id"] for r in selected}
        rest = sorted(
            (r for plen, r in eligible if r["instance_id"] not in chosen_ids),
            key=lambda r: (patch_line_count(r["patch"]), r["instance_id"]),
        )
        for r in rest:
            if len(selected) >= train_size:
                break
            selected.append(r)

                              
    selected.sort(key=lambda r: r["instance_id"])
    return selected

def save_jsonl(data: list, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            ordered = {k: item[k] for k in OUTPUT_FIELDS}
            f.write(json.dumps(ordered, ensure_ascii=False) + "\n")
    print(f"   saved {len(data)}  items → {path}")

def load_records(dataset: str, split: str, local_parquet: str) -> list:
    """loadraw data: prefer HuggingFace datasets, failedthen rolled back to local  parquet.

    returned  dict columntable,  and datasourceno .
    """
                                 
    try:
        from datasets import load_dataset
        ds = load_dataset(dataset, split=split)
        return [dict(row) for row in ds]
    except Exception as e:
        print(f"  online loadfailed ({type(e).__name__}: {e}) ")
        local = Path(local_parquet)
        if not local.exists():
            raise RuntimeError(
                f"at loadfailed and local  parquet not found: {local}\n"
                f"first , examplelike : \n"
                f'  curl -L -o "{local}" \\\n'
                f'    "$HF_ENDPOINT/datasets/{dataset}/resolve/main/data/test-00000-of-00001.parquet"\n'
                f" (HF_ENDPOINT can  as  https://hf-mirror.com) "
            ) from e
        print(f"  ↩  fallback to local  parquet: {local}")
        import pandas as pd
        df = pd.read_parquet(local)
        return df.to_dict(orient="records")

def main():
    parser = argparse.ArgumentParser(description="build SWE-bench Verified verify dataset")
    parser.add_argument("--train-size", type=int, default=20, help="train sample count (default 20) ")
    parser.add_argument("--per-repo", type=int, default=5, help="per  repoat most selected items count (default 5) ")
    parser.add_argument("--max-patch-lines", type=int, default=30, help="gold patch max line count (default 30) ")
    parser.add_argument("--min-ps", type=int, default=500, help="problem_statement min chars count (default 500) ")
    parser.add_argument("--max-ps", type=int, default=3000, help="problem_statement max chars count (default 3000) ")
    parser.add_argument("--dataset", type=str, default="princeton-nlp/SWE-bench_Verified",
                        help="HuggingFace datasetname")
    parser.add_argument("--split", type=str, default="test", help="dataset split (default test) ")
    parser.add_argument("--local-parquet", type=str,
                        default=str(OUTPUT_DIR / "raw" / "test-00000-of-00001.parquet"),
                        help="local  parquet path (networknot can use  fallback datasource) ")
    args = parser.parse_args()

    print("=" * 60)
    print("SWE-bench Verified dataset build")
    print("=" * 60)
    print(f"  dataset: {args.dataset} (split={args.split})")
    print(f"  train target: {args.train_size}  items, per repo ≤ {args.per_repo}  items")
    print(f"  patch line count ≤ {args.max_patch_lines}, problem_statement {args.min_ps}~{args.max_ps} chars")
    if os.environ.get("HF_ENDPOINT"):
        print(f"  HF_ENDPOINT: {os.environ['HF_ENDPOINT']}")

    print(f"\n loaddataset ...")
    ds = load_records(args.dataset, args.split, args.local_parquet)
    print(f"  loaded {len(ds)}  itemsraw data")

             
    records = [normalize_record(row) for row in ds]

              
    print(f"\n select by strategy train samples ...")
    train = select_train(
        records, args.train_size, args.per_repo,
        args.max_patch_lines, args.min_ps, args.max_ps,
    )
    if len(train) < args.train_size:
        print(f"  only selected  {len(train)}  items (target {args.train_size}) , relax the constraints")

                 
    train_ids = {r["instance_id"] for r in train}
    test = [r for r in records if r["instance_id"] not in train_ids]
    test.sort(key=lambda r: r["instance_id"])

        
    print(f"\n save dataset ...")
    save_jsonl(train, OUTPUT_DIR / "train.jsonl")
    save_jsonl(test, OUTPUT_DIR / "test.jsonl")

        
    print(f"\n dataset stats:")
    repo_dist = {}
    patch_lens = []
    for r in train:
        repo_dist[r["repo"]] = repo_dist.get(r["repo"], 0) + 1
        patch_lens.append(patch_line_count(r["patch"]))
    print(f"  train repo distribution:")
    for repo, cnt in sorted(repo_dist.items(), key=lambda x: (-x[1], x[0])):
        print(f"    {repo}: {cnt}")
    avg_patch = sum(patch_lens) / len(patch_lens) if patch_lens else 0
    print(f"  train avg patch length: {avg_patch:.1f}  lines (min={min(patch_lens) if patch_lens else 0}, max={max(patch_lens) if patch_lens else 0})")
    print(f"  train total: {len(train)}")
    print(f"  test  total: {len(test)}")

          
    print(f"\n examples (train top  3  items):")
    for r in train[:3]:
        print(f"  ---")
        print(f"  instance_id: {r['instance_id']}")
        print(f"  repo: {r['repo']} | version: {r['version']}")
        print(f"  patch line count: {patch_line_count(r['patch'])} | problem_statement: {len(r['problem_statement'])} chars")

    print(f"\n done！")

if __name__ == "__main__":
    main()
