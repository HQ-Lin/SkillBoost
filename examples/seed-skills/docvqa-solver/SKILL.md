---
type: task_skill
task_name: DocVQA document image question answering
description: Read a document image and answer the question precisely with evidence visible in the image, outputting the minimal complete exact text span
current_version: v0
parent_version: null
repair_brief: null
evolution_note: "Seed version, ported from the reference implementation and adapted to this framework format"
---

# Task Skill: DocVQA Document Visual QA

## 1. Definition and Scope

**Task definition**: given a document image (form, letter, report, table, receipt, etc.) and a question about it, read the visible content and give the **exact answer**.

**Scoring**: ANLS (Average Normalized Levenshtein Similarity).
- The answer is compared against each reference answer after normalization (lowercasing, extra whitespace removed).
- A similarity of at least 0.5 earns credit, and closer to an exact match scores higher.
- Therefore **one extra character, one missing character, or one wrong digit** costs points noticeably.

**Core principle**: the answer must come from content **visible** in the image. Never fabricate from memory or common sense.

---

## 2. Visual Evidence Discipline

1. **Read before answering**: scan the whole document first and locate the regions relevant to the question (titles, field labels, table rows/columns, signature blocks, date fields).
2. **Minimal exact span**: prefer the **shortest complete** text span that answers the question, without unrelated modifiers.
3. **Nearby-match disambiguation**: when several adjacent strings all look like the answer, pick the one whose **surrounding label or layout** best matches the question.

---

## 3. Exact Answer Discipline

1. **Copy verbatim**: names, numbers, dates, amounts, and IDs should be copied **character by character** from the image.
2. **Extraction over paraphrase**: quote directly whenever possible instead of rewriting.
3. **Compare before finalizing**: re-check the answer against nearby candidates in the image and keep the exact span with the strongest evidence.

---

## 4. Answering Workflow (SOP)

### Step 1: Understand the question
- Identify the answer type (person / organization / date / number / amount / yes-no / list).
- Capture the key constraint words in the question (such as "To Address", "departure date", "president of X").

### Step 2: Locate the evidence region
- Find the **field label** or **layout position** matching the question keywords.
- Read the value adjacent to that label.

### Step 3: Extract the exact answer
- Quote the minimal complete span, keeping original casing and punctuation (unless the question requires otherwise).
- Copy numbers and dates exactly in the format shown in the image.

### Step 4: Self-check and output
- Check for extra/missing characters or misplaced digits.
- Check for off-topic answers or picking an adjacent distractor.

---

## 5. Common Failures and Avoidance

| Failure type | Description | Avoidance |
|--------------|-------------|-----------|
| evidence_miss | Overlooked a relevant visible region or row | Scan the whole image systematically by field labels |
| near_match_confusion | Picked an adjacent but wrong text span | Verify label match with the question constraints |
| normalization_error | Answer differs only in format/whitespace/punctuation/case | Copy verbatim, avoid rewriting |
| reading_error | Misread characters in the document | Zoom into the target region and verify character by character |

---

## 6. Output Format

Put the final answer inside `<answer>...</answer>`, containing **only the answer itself**, without explanations or prefixes/suffixes.

Examples:
- Question: What is the name of factory? -> `<answer>Gering</answer>`
- Question: What is the departure date? -> `<answer>7/10/76</answer>`
