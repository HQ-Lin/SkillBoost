#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path

SOURCE_DIR = Path("/path/to/source_data/officeqa_split")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "officeqa"

def split_multi(value: str) -> list:
    """ CSV single  multi-valuefieldcolumntable (compatible JSON  countgroup / swap  lines / ) .

    note: source_docs  is  URL, in can can with , not use comma separated, only use swap  lines and .
    """
    v = str(value or "").strip()
    if not v:
        return []
                  
    try:
        loaded = json.loads(v)
        if isinstance(loaded, list):
            return [str(x).strip() for x in loaded if str(x).strip()]
    except json.JSONDecodeError:
        pass
    parts = re.split(r"[\n;]+", v)
    return [p.strip() for p in parts if p.strip()]

def convert(split: str) -> list:
    csv_path = SOURCE_DIR / split / "officeqa.csv"
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        out.append({
            "task_id": r["uid"].strip(),
            "question": r["question"].strip(),
            "gold_answer": r["answer"].strip(),
            "source_files": split_multi(r["source_files"]),
            "source_docs": split_multi(r["source_docs"]),
            "difficulty": r["difficulty"].strip(),
        })
    return out

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for split in ["train", "val", "test"]:
        csv_path = SOURCE_DIR / split / "officeqa.csv"
        if not csv_path.exists():
            print(f"skipped {split}: {csv_path} not found")
            continue
        data = convert(split)
        out_path = OUTPUT_DIR / f"{split}_agentic.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for d in data:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        n_multi_doc = sum(1 for d in data if len(d["source_docs"]) > 1)
        n_multi_file = sum(1 for d in data if len(d["source_files"]) > 1)
        print(f"{split}: {len(data)}  items → {out_path}  (multi-page evidence={n_multi_doc}, multi-file={n_multi_file})")

if __name__ == "__main__":
    main()
