#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import Counter

ALFWORLD_ROOT = Path("/path/to/cache/alfworld/json_2.1.1")
SOURCE_TEST = Path(
    "/path/to/data/ablation_splits/alfworld/2-1-7_seed42/test/items.json"
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
    """from  gamefile pathextracttask type (at directoryname in ) . """
                                                                                                
                      
    path = Path(gamefile)
    parent_name = path.parent.parent.name           
    for t in TASKS:
        if t in parent_name:
            return t
    return "other"

def build_from_official_train():
    """from official  train directorybuild testset. """
    train_dir = ALFWORLD_ROOT / "train"
    if not train_dir.exists():
        raise FileNotFoundError(f"official  train directory not found: {train_dir}")

    games = []
    for task_dir in sorted(train_dir.iterdir()):
        if task_dir.is_dir():
            task_name = task_type(str(task_dir.name))
            if task_name in TASKS:
                games.append({
                    "gamefile": str(task_dir / "traj_data.json"),
                    "task_type": task_name,
                })

    return games

def build_from_source_test():
    """Build the test set from the ablation test split."""
    if not SOURCE_TEST.exists():
        raise FileNotFoundError(f"source test file not found: {SOURCE_TEST}")

    items = json.load(open(SOURCE_TEST))
    games = []
    for item in items:
        gamefile = item["gamefile"]
        tt = task_type(gamefile)
        if tt in TASKS:
            games.append({
                "gamefile": gamefile,
                "task_type": tt,
            })

    return games

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("build  ALFWorld official test set (706 )")
    print("=" * 70)

                                            
    print("\n data source: ablation test split")
    games = build_from_source_test()
    print(f"  total game  count: {len(games)}")

             
    type_counts = Counter(g["task_type"] for g in games)
    print("\n task typedistribution:")
    for t in TASKS:
        print(f"  {t}: {type_counts[t]}")

                 
                          
    target_count = 706
    if len(games) > target_count:
        print(f"\n target: from  {len(games)}  items sampled  {target_count}  items (by task typeratio) ")

                 
        by_type = {}
        for g in games:
            by_type.setdefault(g["task_type"], []).append(g)

                    
        sampled = []
        remaining = target_count
        for i, t in enumerate(TASKS):
            type_games = by_type.get(t, [])
            if i < len(TASKS) - 1:
                       
                count = int(target_count * len(type_games) / len(games))
                count = min(count, len(type_games))
            else:
                           
                count = min(remaining, len(type_games))

            sampled.extend(type_games[:count])
            remaining -= count

        games = sampled
        print(f"  after samplingtotal: {len(games)}")

               
    output_file = OUT_DIR / "official_test_706.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for i, g in enumerate(games):
            row = {
                "id": f"alf_{g['task_type']}_{i:04d}",
                "gamefile": g["gamefile"],
                "task_type": g["task_type"],
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n written: {output_file}")
    print(f"   total items count: {len(games)}")

            
    final_count = sum(1 for _ in open(output_file))
    print(f"  verify line count: {final_count}")

            
    final_types = Counter()
    for line in open(output_file):
        data = json.loads(line)
        final_types[data["task_type"]] += 1
    print("\n final task typedistribution:")
    for t in TASKS:
        print(f"  {t}: {final_types[t]}")

    print("=" * 70)

if __name__ == "__main__":
    main()
