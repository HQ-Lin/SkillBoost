#!/usr/bin/env python3
import argparse
import json
import random
import re
import string
from pathlib import Path

                                                         
    
                                                         

SOURCE_PATH = Path("/path/to/data/searchqa_full/train/items.jsonl")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "searchqa"

MAX_CONTEXT_CHARS = 6000           

                                                         
      
                                                         

def normalize_answer(s: str) -> str:
    """SQuAD normalized answer (use at compare) """
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = " ".join(s.split())
    return s.strip()

def truncate_context(context: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """by  [DOC] boundarytruncatecontextto specified chars count"""
    if len(context) <= max_chars:
        return context

    docs = context.split("[DOC]")
    result = ""
    for doc in docs:
        candidate = result + "[DOC]" + doc if result else doc
        if len(candidate) > max_chars:
            break
        result = candidate

    return result if result else context[:max_chars]

def has_overlap(answer_a: str, answer_b: str) -> bool:
    """checktwo  answer is whether has semantic overlap (normalize after with ) """
    norm_a = normalize_answer(answer_a)
    norm_b = normalize_answer(answer_b)
    if not norm_a or not norm_b:
        return True           
    return norm_a in norm_b or norm_b in norm_a

def extract_candidate_entities(context: str, gold_answers: list) -> list:
    """
    from context in extractcan can  as  hard negatives.
    strategy: extractlarge start , ref content,  count etc.
    """
    candidates = []

              
    quoted = re.findall(r'"([^"]{2,40})"', context)
    candidates.extend(quoted)

                              
    capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b', context)
    candidates.extend(capitalized)

          
    years = re.findall(r'\b(1[0-9]{3}|20[0-2][0-9])\b', context)
    candidates.extend(years)

             
    numbers = re.findall(r'\b(\d+(?:\.\d+)?(?:\s*(?:million|billion|thousand|percent|%|km|miles))?)\b', context)
    candidates.extend([n for n in numbers if len(n) > 1])

                         
    seen = set()
    filtered = []
    for c in candidates:
        c = c.strip()
        if not c or len(c) < 2 or len(c) > 50:
            continue
        norm_c = normalize_answer(c)
        if norm_c in seen:
            continue
                             
        overlap = False
        for gold in gold_answers:
            if has_overlap(c, gold):
                overlap = True
                break
        if not overlap:
            seen.add(norm_c)
            filtered.append(c)

    return filtered

def load_source_data(path: Path, max_lines: int = 0) -> list:
    """loadraw  SearchQA data"""
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
                        
            if not item.get("answers") or not item["answers"][0].strip():
                continue
            items.append(item)
            if max_lines and len(items) >= max_lines:
                break
    return items

def build_dataset(items: list, split_name: str, start_idx: int, size: int, all_answers: list) -> list:
    """
    from  items[start_idx:start_idx+size] buildbinary splitclassdataset.
    per  questionsgenerate  1 example + 1 example.

    examplestrategy (by priority) :
    1. Hard negative: from context in extractout  (not  is correctanswer)
    2. Same-type fallback: from otherquestions answer in sampling

    Args:
        items: raw datacolumntable
        split_name: datasetsplitname (train/test)
        start_idx: ref
        size: samplingquestions count
        all_answers: allanswer pool (use at  fallback samplingnoiseitem)

    Returns:
        buildgood  case columntable
    """
    cases = []
    selected = items[start_idx:start_idx + size]
    hard_neg_count = 0

    for i, item in enumerate(selected):
        question = item["question"]
        context = truncate_context(item["context"])
        gold_answer = item["answers"][0]          
        gold_answers = item["answers"]
        base_id = f"searchqa_{split_name}_{i:03d}"

                                  
        cases.append({
            "task_id": f"{base_id}_correct",
            "question": question,
            "context": context,
            "candidate_answer": gold_answer,
            "investigate_result": 1,                         
            "gold_answers": gold_answers,
        })

                                   
        distractor = None
        context_entities = extract_candidate_entities(context, gold_answers)
        if context_entities:
                               
            distractor = random.choice(context_entities)
            hard_neg_count += 1
        else:
                                   
            distractor = sample_distractor(gold_answers, all_answers)

        cases.append({
            "task_id": f"{base_id}_incorrect",
            "question": question,
            "context": context,
            "candidate_answer": distractor,
            "investigate_result": 2,                        
            "gold_answers": gold_answers,
        })

    print(f"    Hard negatives (from context): {hard_neg_count}/{size} ({hard_neg_count/size*100:.0f}%)")
    return cases

def sample_distractor(gold_answers: list, all_answers: list, max_attempts: int = 50) -> str:
    """
    from answer pool in samplingone  and  gold_answers no semantic overlap noiseanswer.
    """
    for _ in range(max_attempts):
        candidate = random.choice(all_answers)
                                
        overlap = False
        for gold in gold_answers:
            if has_overlap(candidate, gold):
                overlap = True
                break
        if not overlap:
            return candidate

                               
    for _ in range(100):
        candidate = random.choice(all_answers)
        if normalize_answer(candidate) != normalize_answer(gold_answers[0]):
            return candidate
    return random.choice(all_answers)

def save_jsonl(data: list, path: Path):
    """save  as  JSONL format"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"   saved {len(data)}  items → {path}")

                                                         
     
                                                         

def main():
    parser = argparse.ArgumentParser(description="build SearchQA binary splitclassdataset")
    parser.add_argument("--size", type=int, default=100,
                        help="per  splitsampling questions count (default 100,  200  items case) ")
    parser.add_argument("--seed", type=int, default=42,
                        help="random seed (default 42) ")
    parser.add_argument("--source", type=str, default=str(SOURCE_PATH),
                        help=f"raw datapath (default {SOURCE_PATH}) ")
    args = parser.parse_args()

    random.seed(args.seed)
    source_path = Path(args.source)

    print("=" * 60)
    print("SearchQA dataset build")
    print("=" * 60)
    print(f"  sourcedata: {source_path}")
    print(f"  sample size: {args.size} questions/split × 2 cases = {args.size * 2} cases/split")
    print(f"  random seed: {args.seed}")

                                          
    load_count = max(args.size * 4, 2000)
    print(f"\n loadraw data (at most  {load_count} )...")
    items = load_source_data(source_path, max_lines=load_count)
    print(f"  loaded {len(items)}  valid items")

    if len(items) < args.size * 2:
        print(f"  datainsufficient！need  {args.size * 2}  items, only has  {len(items)}  items")
        return

          
    random.shuffle(items)

                             
    all_answers = [item["answers"][0] for item in items]
    print(f"  answer pool size: {len(all_answers)}")

                     
    print(f"\n build train dataset ({args.size} questions → {args.size * 2} cases) ...")
    train_cases = build_dataset(items, "train", 0, args.size, all_answers)

    print(f"build test dataset ({args.size} questions → {args.size * 2} cases) ...")
    test_cases = build_dataset(items, "test", args.size, args.size, all_answers)

        
    print(f"\n save dataset...")
    save_jsonl(train_cases, OUTPUT_DIR / "train.jsonl")
    save_jsonl(test_cases, OUTPUT_DIR / "test.jsonl")

          
    print(f"\n dataset stats:")
    for name, cases in [("train", train_cases), ("test", test_cases)]:
        correct = sum(1 for c in cases if c["investigate_result"] == 1)
        incorrect = sum(1 for c in cases if c["investigate_result"] == 2)
        print(f"  {name}: {len(cases)} cases (correct={correct}, incorrect={incorrect})")

          
    print(f"\n examples (train top  2  items):")
    for case in train_cases[:2]:
        print(f"  ---")
        print(f"  task_id: {case['task_id']}")
        print(f"  question: {case['question'][:80]}...")
        print(f"  candidate: {case['candidate_answer']}")
        print(f"  label: {'correct' if case['investigate_result'] == 1 else 'incorrect'}")

    print(f"\n done！")

if __name__ == "__main__":
    main()
