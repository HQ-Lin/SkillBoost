#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

SRC_SPLITS = Path(
    "/path/to/data/ablation_splits/"
    "livemathematicianbench/2-1-7_seed42"
)
OUT_DIR = Path(__file__).parent.parent / "data" / "livemath"

CHOICE_LABELS = ["A", "B", "C", "D", "E", "F", "G"]

def _normalize_label(text: str) -> str:
    return str(text).strip().upper().rstrip(".):")

def _coerce_choices(raw_choices) -> list[dict]:
    choices: list[dict] = []
    if isinstance(raw_choices, list):
        for idx, item in enumerate(raw_choices):
            if isinstance(item, dict):
                label = str(item.get("label") or CHOICE_LABELS[idx]).strip()
                text = str(item.get("text") or item.get("content") or "").strip()
            else:
                label = CHOICE_LABELS[idx] if idx < len(CHOICE_LABELS) else str(idx)
                text = str(item).strip()
            if text:
                choices.append({"label": label, "text": text})
    elif isinstance(raw_choices, dict):
        for label in sorted(raw_choices.keys()):
            text = str(raw_choices[label]).strip()
            if text:
                choices.append({"label": str(label).strip(), "text": text})
    return choices

def _item_shuffle_seed(item_id: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{item_id}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)

def _shuffle_choices(choices: list[dict], correct_label: str, item_id: str, seed: int) -> tuple[list[dict], str, str]:
    """for optionitemper  questions,  and new  label (consistent with the reference dataloader). """
    shuffled = [dict(c) for c in choices]
    rng = random.Random(_item_shuffle_seed(item_id, seed))
    rng.shuffle(shuffled)

    original_correct = _normalize_label(correct_label)
    remapped: list[dict] = []
    new_correct_label = original_correct
    new_correct_text = ""
    for idx, choice in enumerate(shuffled):
        new_label = CHOICE_LABELS[idx]
        old_label = _normalize_label(choice["label"])
        remapped.append({"label": new_label, "text": choice["text"]})
        if old_label == original_correct:
            new_correct_label = new_label
            new_correct_text = choice["text"]
    return remapped, new_correct_label, new_correct_text

def build_split(split: str, shuffle_choices: bool, seed: int) -> list[dict]:
    path = SRC_SPLITS / split / "qa_all_final.json"
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    cases: list[dict] = []
    for row_idx, item in enumerate(raw):
        mcq = item.get("mcq", {}) if isinstance(item.get("mcq"), dict) else {}
        question = str(mcq.get("question") or item.get("question") or "").strip()
        choices = _coerce_choices(mcq.get("choices") or item.get("choices") or [])
        correct = mcq.get("correct_choice") or item.get("correct_choice") or {}
        if isinstance(correct, dict):
            correct_label = _normalize_label(correct.get("label", ""))
            correct_text = str(correct.get("text") or "").strip()
        else:
            correct_label = _normalize_label(correct)
            correct_text = ""

        choice_by_label = {_normalize_label(c["label"]): c["text"] for c in choices}
        if correct_label and not correct_text:
            correct_text = choice_by_label.get(correct_label, "")

                                                        
                                                
                                                                   
        if correct_label and correct_text and correct_label not in choice_by_label:
            choices.append({"label": correct_label, "text": correct_text})
            choices.sort(key=lambda c: CHOICE_LABELS.index(c["label"])
                         if c["label"] in CHOICE_LABELS else len(CHOICE_LABELS))
            choice_by_label[correct_label] = correct_text

        if not (question and choices and correct_label):
            continue

        month = str(item.get("month") or "").strip()
        item_no = item.get("no", row_idx + 1)
        task_id = f"livemath_{split}_{month}_{item_no}" if month else f"livemath_{split}_{item_no}"

        theorem_type = item.get("theorem_type", [])
        if isinstance(theorem_type, str):
            theorem_type = [theorem_type] if theorem_type else []
        elif theorem_type is None:
            theorem_type = []
        theorem_type = [str(t).strip() for t in theorem_type if str(t).strip()]

        if shuffle_choices:
            choices, correct_label, ct = _shuffle_choices(choices, correct_label, task_id, seed)
            if ct:
                correct_text = ct

        cases.append({
            "task_id": task_id,
            "question": question,
            "choices": choices,
            "correct_label": correct_label,
            "correct_text": correct_text,
            "theorem_type": theorem_type,
            "month": month,
            "source_split": split,
        })
    print(f"  [{split}] cases={len(cases)} (shuffle_choices={shuffle_choices})")
    return cases

def save_jsonl(cases: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"   saved {len(cases)}  items → {path}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Build the LiveMath jsonl dataset.")
    parser.add_argument("--seed", type=int, default=42, help="optionitemsub  (reference default is 42)")
    parser.add_argument("--no-shuffle-choices", action="store_true",
                        help="use optionitem (defaulton, prevent position) ")
    args = parser.parse_args()

    shuffle_choices = not args.no_shuffle_choices

    print("=" * 60)
    print("LiveMathematicianBench dataset build")
    print("=" * 60)
    print(f"  source: {SRC_SPLITS}")
    print(f"  target: {OUT_DIR}")
    print(f"  shuffle_choices={shuffle_choices}  seed={args.seed}")

    for split in ("train", "val", "test"):
        cases = build_split(split, shuffle_choices, args.seed)
        save_jsonl(cases, OUT_DIR / f"{split}.jsonl")

    print("\n done！")

if __name__ == "__main__":
    main()
