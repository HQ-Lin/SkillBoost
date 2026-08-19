#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "olympiadbench" / "raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "olympiadbench"

                           
DATA_FILES = [
    "test.parquet",        
                 
]

def load_raw_data(raw_dir: Path) -> list[dict]:
    """loadallraw datafile (support parquet  and  json) . """
    all_items = []
    
    for filename in DATA_FILES:
        filepath = raw_dir / filename
        if not filepath.exists():
            print(f"file not found: {filepath}")
            continue
        
                       
        if filename.endswith('.parquet'):
            import pandas as pd
            df = pd.read_parquet(filepath)
                     
            data = df.to_dict('records')
            print(f"load {filename}: {len(data)}  questions (parquetformat)")
                    
        elif filename.endswith('.json'):
            with filepath.open(encoding="utf-8") as f:
                data = json.load(f)
            print(f"load {filename}: {len(data)}  questions (jsonformat)")
        else:
            print(f"unsupported fileformat: {filename}")
            continue
        
        all_items.extend(data)
    
    return all_items

def normalize_answer(answer: str | list) -> str:
    """normalized answerformat. """
    if isinstance(answer, list):
                     
        answer = answer[0] if answer else ""
    
                   
    answer = str(answer).strip()
    answer = answer.replace("$", "").replace("\\", "")
    
    return answer

def build_splits(all_items: list[dict], train_ratio: float = 0.7, val_ratio: float = 0.15, seed: int = 42):
    """ train/val/test dataset. """
    random.seed(seed)
    random.shuffle(all_items)
    
    n = len(all_items)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_items = all_items[:train_end]
    val_items = all_items[train_end:val_end]
    test_items = all_items[val_end:]
    
    return {
        "train": train_items,
        "val": val_items,
        "test": test_items,
    }

def convert_to_jsonl(items: list[dict], split_name: str) -> list[dict]:
    """convert as itemtarget  jsonl format. """
    jsonl_items = []
    
    for idx, item in enumerate(items):
                        
        final_answer = item.get("final_answer", "")
        if isinstance(final_answer, list):
            final_answer = final_answer[0] if final_answer else ""
        normalized_ans = normalize_answer(final_answer)
        
                          
        solution = item.get("solution", "")
        if isinstance(solution, list):
            solution_text = "\n\n".join(str(s) for s in solution)
        else:
            solution_text = str(solution)
        
                                              
        modality = item.get("modality", "")
        if modality != "Text-only":
            continue
        
        jsonl_item = {
            "task_id": f"olympiad_{split_name}_{idx+1:04d}",
            "question": str(item.get("question", "")).strip(),
            "subfield": item.get("subfield", "Unknown"),
            "answer_type": item.get("answer_type", "Unknown"),
            "final_answer": normalized_ans,
            "solution": solution_text,
            "is_multiple_answer": item.get("is_multiple_answer", False),
            "unit": item.get("unit"),
            "source_split": split_name,
            "difficulty": item.get("difficulty", "Unknown"),
            "subject": item.get("subject", "Math"),
            "language": item.get("language", "en"),
        }
        
                   
        if not jsonl_item["question"] or not jsonl_item["final_answer"]:
            continue
        
        jsonl_items.append(jsonl_item)
    
    return jsonl_items

def save_jsonl(items: list[dict], output_path: Path):
    """save  as  jsonl file. """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"save  {len(items)}  questionsto  {output_path}")

def main():
    parser = argparse.ArgumentParser(description="build  OlympiadBench dataset")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="raw datadirectory")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help="output directory")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="setratio")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="verify setratio")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()
    
    print("=" * 60)
    print("OlympiadBench datasetbuild ")
    print("=" * 60)
    
               
    print("\n steps 1: loadraw data")
    all_items = load_raw_data(args.raw_dir)
    
    if not all_items:
        print("\n error: not found:any datafile")
        print(f"put datafilein to  {args.raw_dir} directory")
        print("\n supported file:")
        for f in DATA_FILES:
            print(f"  - {f}")
        return
    
    print(f"\n totalload: {len(all_items)}  questions")
    
                                
    print(f"\n steps 2: use full dataas the test set")
    splits = {
        "test": all_items,
    }
    
    for split_name, items in splits.items():
        print(f"  - {split_name}: {len(items)}  questions (raw ) ")
    
              
    print(f"\n steps 3: convert and save as jsonl format")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    for split_name, items in splits.items():
        jsonl_items = convert_to_jsonl(items, split_name)
        output_path = args.out_dir / f"{split_name}.jsonl"
        save_jsonl(jsonl_items, output_path)
    
             
    print(f"\n{'=' * 60}")
    print("dataset stats")
    print(f"{'=' * 60}")
    
    total = 0
    for split_name in ["train", "val", "test"]:
        output_path = args.out_dir / f"{split_name}.jsonl"
        if output_path.exists():
            with output_path.open(encoding="utf-8") as f:
                count = sum(1 for _ in f)
            total += count
            print(f"  {split_name}: {count}  questions")
    
    print(f"\n total: {total}  questions")
    print(f"output directory: {args.out_dir}")
    print(f"\n next  steps: run evaluationscript")
    print(f"   conda run -n evolution python benchmarks/evaluators/test_olympiadbench.py \\")
    print(f"       --data {args.out_dir}/test.jsonl \\")
    print(f"       --skill outputs/olympiad_noskill \\")
    print(f"       --model qwen3.7-max \\")
    print(f"       --max-concurrent 10")

if __name__ == "__main__":
    main()
