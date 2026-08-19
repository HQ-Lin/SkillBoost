#!/usr/bin/env python3
import json
import random
from pathlib import Path

SKILLOPT_SPLIT = Path(
    "/path/to/data/ablation_splits/alfworld/2-1-7_seed42"
)
OUT_DIR = Path(__file__).parent.parent / "data" / "alfworld"

TASKS = [
    "pick_and_place",
    "pick_two_obj_and_place",
    "look_at_obj_in_light",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_clean_then_place_in_recep",
]

def task_type(gamefile: str) -> str:
    for t in TASKS:
        if t in gamefile:
            return t
    return "other"

def sample_balanced(items, per_type, seed, exclude=None):
    exclude = exclude or set()
    by_type = {t: [] for t in TASKS}
    for it in items:
        tt = task_type(it["gamefile"])
        if tt in by_type and it["gamefile"] not in exclude:
            by_type[tt].append(it)
    rng = random.Random(seed)
    picked = []
    for t in TASKS:
        pool = by_type[t]
        rng.shuffle(pool)
        picked.extend(pool[:per_type])
    return picked

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train_src = json.load(open(SKILLOPT_SPLIT / "train" / "items.json"))
    test_src = json.load(open(SKILLOPT_SPLIT / "test" / "items.json"))

    train_pick = sample_balanced(train_src, per_type=5, seed=42)
    train_files = {x["gamefile"] for x in train_pick}
    test_pick = sample_balanced(test_src, per_type=6, seed=123, exclude=train_files)

    def dump(picks, path):
        with open(path, "w", encoding="utf-8") as f:
            for i, it in enumerate(picks):
                tt = task_type(it["gamefile"])
                row = {
                    "id": f"alf_{tt}_{i:03d}",
                    "gamefile": it["gamefile"],
                    "task_type": tt,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"wrote {len(picks)} -> {path}")

    dump(train_pick, OUT_DIR / "train.jsonl")
    dump(test_pick, OUT_DIR / "test.jsonl")

if __name__ == "__main__":
    main()
