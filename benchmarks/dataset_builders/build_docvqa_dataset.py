#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import json
import random
import shutil
from pathlib import Path

SRC_ROOT = Path("/path/to/source_data/docvqa")
SRC_SPLITS = SRC_ROOT / "splits"
OUT_DIR = Path(__file__).parent.parent / "data" / "docvqa"
OUT_IMAGES = OUT_DIR / "images"

def parse_answers(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except Exception:
        return [text]
    if isinstance(parsed, list):
        return [str(x).strip() for x in parsed if str(x).strip()]
    return [str(parsed).strip()]

def load_csv(split: str) -> list[dict]:
    path = SRC_SPLITS / split / "docvqa.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def build_split(split: str, size: int, seed: int) -> list[dict]:
    rows = load_csv(split)
    rng = random.Random(seed)
    rng.shuffle(rows)
    selected = rows[:size] if size > 0 else rows

    OUT_IMAGES.mkdir(parents=True, exist_ok=True)
    cases = []
    copied = 0
    for i, row in enumerate(selected):
        qid = str(row.get("questionId") or row.get("id") or i).strip()
        answers = parse_answers(row.get("answer") or "")
        if not answers:
            continue
        src_img = Path(row.get("image_path") or "")
        if not src_img.exists():
            continue
        dst_img = OUT_IMAGES / src_img.name
        if not dst_img.exists():
            shutil.copy2(src_img, dst_img)
            copied += 1
        cases.append({
            "task_id": f"docvqa_{split}_{qid}",
            "question": str(row.get("question") or "").strip(),
            "answers": answers,
            "image_path": str(dst_img.resolve()),
            "topic": str(row.get("topic") or "docvqa").strip(),
            "source_split": split,
        })
    print(f"  [{split}] selected={len(cases)} images_copied={copied}")
    return cases

def save_jsonl(cases: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"   saved {len(cases)}  items → {path}")

def main() -> None:
    parser = argparse.ArgumentParser(description="build DocVQA jsonl dataset (with figuresub set) ")
    parser.add_argument("--train", type=int, default=150)
    parser.add_argument("--val", type=int, default=100)
    parser.add_argument("--test", type=int, default=150)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("=" * 60)
    print("DocVQA dataset build")
    print("=" * 60)
    print(f"  source: {SRC_SPLITS}")
    print(f"  target: {OUT_DIR}")
    print(f"  sampling: train={args.train} val={args.val} test={args.test} seed={args.seed}")

    for split, size in (("train", args.train), ("val", args.val), ("test", args.test)):
        cases = build_split(split, size, args.seed)
        save_jsonl(cases, OUT_DIR / f"{split}.jsonl")

    print("\n done！")

if __name__ == "__main__":
    main()
