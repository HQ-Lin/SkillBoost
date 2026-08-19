#!/usr/bin/env python
import json
from pathlib import Path

                                                                    
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "bfcl"

CATEGORIES = [
    "BFCL_v4_multi_turn_base",
    "BFCL_v4_multi_turn_miss_func",
    "BFCL_v4_multi_turn_miss_param",
    "BFCL_v4_multi_turn_long_context",
]

TRAIN_PER_CATEGORY = 100

def load_jsonl(path: Path):
    """Load a JSONL file (one JSON object per line)."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records

def load_test_ids(path: Path):

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        ids = data.get("ids", [])
    else:
        ids = data
    return set(ids)

def main():
                             
    all_data = {}
    for cat in CATEGORIES:
        all_data[cat] = load_jsonl(DATA_DIR / f"{cat}.json")

                    
    test_ids = load_test_ids(DATA_DIR / "testset_v1.json")

    train_records = []
    test_records = []
    per_cat_stats = {}

    for cat, records in all_data.items():
        cat_train_pool = []
        cat_test = []
        for r in records:
            rid = r.get("id", "")
            if rid in test_ids:
                cat_test.append(r)
            else:
                cat_train_pool.append(r)
        cat_train = cat_train_pool[:TRAIN_PER_CATEGORY]
        train_records.extend(cat_train)
        test_records.extend(cat_test)
        per_cat_stats[cat] = {
            "total": len(records),
            "train": len(cat_train),
            "test": len(cat_test),
        }

    with open(DATA_DIR / "train.jsonl", "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(DATA_DIR / "test.jsonl", "w", encoding="utf-8") as f:
        for r in test_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("Per-category split:")
    for cat, s in per_cat_stats.items():
        print(f"  {cat}: total={s['total']} train={s['train']} test={s['test']}")
    print(f"Train: {len(train_records)} records -> {DATA_DIR / 'train.jsonl'}")
    print(f"Test : {len(test_records)} records -> {DATA_DIR / 'test.jsonl'}")
    print(f"Test ids in manifest: {len(test_ids)}")

if __name__ == "__main__":
    main()
