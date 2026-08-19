#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
from pathlib import Path

                                                         
    
                                                         

SOURCE_DIR = Path("/path/to/data/officeqa_split")
DOCS_DIR = Path("/path/to/data/officeqa_docs_official")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "officeqa"

                   
MAX_CHARS_PER_FILE = 80000               
           
MAX_TOTAL_CHARS = 150000               

                    
WINDOW_BEFORE = 1500
WINDOW_AFTER = 3500

                                                         
            
                                                         

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "what", "from", "into",
    "was", "were", "are", "is", "of", "in", "on", "to", "by", "an", "a",
    "as", "at", "or", "be", "it", "its", "than", "between", "during",
    "which", "how", "many", "much", "shown", "given", "report", "reports",
    "table", "value", "values", "balance", "balances", "page", "issue",
    "calculate", "compute", "compared", "do", "does", "did", "you", "your",
    "us", "u.s.", "round", "decimal", "answer", "format", "express", "result",
    "if", "no", "yes", "have", "has", "had", "their", "where", "when", "use",
    "using", "based", "amount", "amounts", "total", "totals", "show",
}

def extract_keywords(question: str) -> list:
    """from  question extractretrievalkeyword (with multi-) . """
    keywords = []
              
    keywords += re.findall(r"\b(?:18|19|20)\d{2}\b", question)
            
    keywords += re.findall(r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b", question)
                                                       
    multi = re.findall(
        r"\b[A-Z][A-Za-z]+(?:\s+(?:of|and|the|in|on|for|to|by)\s+)?(?:\s+[A-Z][A-Za-z]+){1,4}\b",
        question,
    )
    keywords += multi
                         
    keywords += re.findall(r"\b[A-Z][A-Za-z][A-Za-z0-9\-]+\b", question)
                               
    keywords += re.findall(r"\b[A-Z]{2,6}\b", question)
                 
    keywords += re.findall(r"\b[a-z]{4,}\b", question.lower())
                  
    keywords += re.findall(r"\b\d{3,}\b", question)
                
    seen, out = set(), []
    for kw in keywords:
        kw_l = kw.lower().strip()
        if len(kw_l) < 3:
            continue
                        
        if " " not in kw_l and kw_l in _STOPWORDS:
            continue
        if kw_l in seen:
            continue
        seen.add(kw_l)
        out.append(kw)
    return out

def smart_extract(text: str, question: str, max_chars: int) -> tuple:
    """
    base at  question keyword windowtake  (sparse has ) :
      1. use keywordretrievaldocs in allhitposition
      2. hit = ( count^2) / (1 + full  times), sparse has  multi-most high
      3. per  hittake  ±window
      4.  and interval, by in totalkeepto  max_chars
      5. keep 4000 chars (keepdirectory/)

    Returns:
        (extracted_text, was_truncated)
    """
    if len(text) <= max_chars:
        return text, False

    keywords = extract_keywords(question)
    if not keywords:
        return text[:max_chars] + "\n\n... [docstruncate]", True

    text_lower = text.lower()
    intervals = []                       
    for kw in keywords:
        kw_l = kw.lower()
        n_words = max(1, len(kw_l.split()))
                 
        total_hits = text_lower.count(kw_l)
        if total_hits == 0:
            continue
        weight = (n_words ** 2) / (1.0 + total_hits)
                        
        start = 0
        n = 0
        while n < 30:
            idx = text_lower.find(kw_l, start)
            if idx == -1:
                break
            s = max(0, idx - WINDOW_BEFORE)
            e = min(len(text), idx + len(kw_l) + WINDOW_AFTER)
            intervals.append((s, e, weight))
            start = idx + len(kw_l)
            n += 1

    if not intervals:
        return text[:max_chars] + "\n\n... [docstruncate]", True

          
    intervals.sort(key=lambda x: x[0])
    merged = []
    for s, e, sc in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e), merged[-1][2] + sc)
        else:
            merged.append((s, e, sc))

    head_keep = 4000
    head = text[:head_keep]
    remaining_budget = max_chars - len(head)

                
    merged_sorted = sorted(merged, key=lambda x: (-x[2], x[0]))
    kept = []
    used = 0
    for s, e, sc in merged_sorted:
        if used >= remaining_budget:
            break
        seg_len = e - s
        if used + seg_len > remaining_budget:
            seg_len = remaining_budget - used
            e = s + seg_len
        kept.append((s, e))
        used += seg_len

    kept.sort(key=lambda x: x[0])
    pieces = [head]
    last_end = head_keep
    for s, e in kept:
        if e <= last_end:
            continue
        if s < last_end:
            s = last_end
        if s > last_end:
            pieces.append(f"\n\n... [skipped {s - last_end} chars] ...\n\n")
        pieces.append(text[s:e])
        last_end = e

    if last_end < len(text):
        pieces.append(f"\n\n... [docstruncate, total  {len(text) - last_end} charsnot with ] ...")

    extracted = "".join(pieces)
    return extracted, True

                                                         
      
                                                         

def load_document(filename: str, question: str, max_chars: int) -> str:
    """loadsingle  docs；when use  question keywordcan take . """
    doc_path = DOCS_DIR / filename
    if not doc_path.exists():
        return ""
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    extracted, _ = smart_extract(text, question, max_chars)
    return extracted

def build_context(source_files_str: str, question: str, max_per_file: int, max_total: int) -> tuple:
    """
    based on  source_files columntablebuild context (by  question can take ) .
    """
    files = [f.strip() for f in source_files_str.strip().split("\n") if f.strip()]

    parts = []
    total_chars = 0
    n_used = 0
    n_truncated = 0

                                                                  
    per_file_budget = max_per_file
    if len(files) > 1:
        per_file_budget = min(max_per_file, int(max_total / len(files) * 1.4))

    for fn in files:
        if total_chars >= max_total:
            break
        remaining = max_total - total_chars
        actual_max = min(per_file_budget, remaining)
        doc = load_document(fn, question, actual_max)
        if not doc:
            continue
        parts.append(f"[FILE: {fn}]\n{doc}")
        total_chars += len(doc)
        n_used += 1
                              
        raw = (DOCS_DIR / fn).read_text(encoding="utf-8", errors="replace")
        if len(raw) > actual_max:
            n_truncated += 1

    context = "\n\n---\n\n".join(parts)
    return context, n_used, n_truncated, len(files)

                                                         
       
                                                         

def build_split(split_name: str, max_per_file: int, max_total: int) -> list:
    """buildone  split (train/val/test)  JSONL data"""
    csv_path = SOURCE_DIR / split_name / "officeqa.csv"
    if not csv_path.exists():
        print(f"   skipped {split_name}: {csv_path} not found")
        return []

    cases = []
    truncated_total = 0
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["uid"]
            context, n_used, n_truncated, n_total = build_context(
                row["source_files"], row["question"], max_per_file, max_total
            )
            if not context:
                print(f"  {uid}: no usable docs, skipped")
                continue

            cases.append({
                "task_id": f"officeqa_{split_name}_{uid}",
                "uid": uid,
                "question": row["question"],
                "context": context,
                "gold_answer": row["answer"],
                "source_files": row["source_files"].strip().split("\n"),
                "n_files_total": n_total,
                "n_files_used": n_used,
                "n_files_truncated": n_truncated,
                "difficulty": row.get("difficulty", "unknown"),
                "context_chars": len(context),
            })
            if n_truncated:
                truncated_total += 1

    print(f"  {split_name}: {len(cases)} cases, {truncated_total} has doc truncation ({truncated_total/max(len(cases),1)*100:.0f}%)")
    return cases

def save_jsonl(data: list, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"   saved {len(data)}  items → {path}")

                                                         
     
                                                         

def main():
    parser = argparse.ArgumentParser(description="build OfficeQA dataset")
    parser.add_argument("--max-chars-per-file", type=int, default=MAX_CHARS_PER_FILE,
                        help=f"single filemax chars count (default {MAX_CHARS_PER_FILE}) ")
    parser.add_argument("--max-total-chars", type=int, default=MAX_TOTAL_CHARS,
                        help=f"totalcontextmax chars count (default {MAX_TOTAL_CHARS}) ")
    args = parser.parse_args()

    print("=" * 60)
    print("OfficeQA dataset build")
    print("=" * 60)
    print(f"  source CSV: {SOURCE_DIR}")
    print(f"  sourcedocs: {DOCS_DIR}")
    print(f"  single filemax chars: {args.max_chars_per_file}")
    print(f"  max total context chars: {args.max_total_chars}")

    if not DOCS_DIR.exists():
        print(f"docsdirectory not found: {DOCS_DIR}")
        sys.exit(1)

    print("\n buildeach  split...")
    all_cases = {}
    for split in ["train", "val", "test"]:
        cases = build_split(split, args.max_chars_per_file, args.max_total_chars)
        all_cases[split] = cases
        if cases:
            save_jsonl(cases, OUTPUT_DIR / f"{split}.jsonl")

          
    print(f"\n dataset stats:")
    for split, cases in all_cases.items():
        if not cases:
            continue
        from collections import Counter
        diff = Counter(c["difficulty"] for c in cases)
        avg_chars = sum(c["context_chars"] for c in cases) / len(cases)
        max_chars = max(c["context_chars"] for c in cases)
        print(f"  {split}: {len(cases)} cases, difficulty={dict(diff)}, "
              f"avg_ctx={avg_chars:.0f} chars, max_ctx={max_chars}")

          
    if all_cases.get("train"):
        print(f"\n examples (train # 1  items):")
        c = all_cases["train"][0]
        print(f"  task_id: {c['task_id']}")
        print(f"  question: {c['question'][:120]}...")
        print(f"  gold_answer: {c['gold_answer']}")
        print(f"  difficulty: {c['difficulty']}")
        print(f"  source_files: {c['source_files']}")
        print(f"  context_chars: {c['context_chars']}")

    print(f"\n done！")

if __name__ == "__main__":
    main()
