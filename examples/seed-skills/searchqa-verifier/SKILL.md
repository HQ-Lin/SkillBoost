---
type: task_skill
task_name: Answer correctness verification
description: Judge whether the candidate answer correctly answers the given question, based on evidence in the search context
---

# Task Skill: SearchQA Answer Verification

## 1. Definition and Scope

**Task definition**: given a question, context snippets returned by a search engine, and a candidate answer, judge whether the candidate answer correctly answers the question.

**Labels**:
- `correct`: the candidate answer is a correct answer to the question
- `incorrect`: the candidate answer is not a correct answer to the question

**Core principle**: judge from factual evidence in the context, not from the model's world knowledge.

---

## 2. Typical Traits of Correct Answers

1. **Direct evidence support**: the context explicitly links the answer to the question
2. **Entity type match**: the answer's entity type (person/place/number/organization) matches what the question asks
3. **Reasonable variants**: the answer is an abbreviation, alias, or short form of the correct answer (such as "Lou Gehrig" vs "(Lou) Gehrig")
4. **Semantic equivalence**: different wording with the same meaning (such as "McDonald's" vs "McDonalds")

---

## 3. Typical Traits of Wrong Answers

1. **Entity type mismatch**: the question asks for a person but the answer is a place, or asks for a year but the answer is a person
2. **Contradicts the context**: the context clearly points to another answer that conflicts with the candidate
3. **Off-target**: the answer appears in the context but is unrelated to the question
4. **No evidence at all**: the context contains no evidence supporting the answer

---

## 4. Judgment Logic (SOP)

### Step 1: Understand the question
- Determine the required answer type (person/place/time/number/organization/thing)
- Identify the key constraints in the question

### Step 2: Scan the context
- Look for factual clues related to the question in the search snippets
- Locate the evidence sentence that directly answers the question

### Step 3: Compare and judge
- Compare the candidate answer against the evidence in the context
- Consider reasonable variants (abbreviations, aliases, punctuation differences)

### Step 4: Output the conclusion
- If the candidate matches the evidence or is a reasonable variant, output `correct`
- If the candidate contradicts the evidence, mismatches the type, or has no support, output `incorrect`

---

## 5. Boundary Cases

| Case | Verdict | Reason |
|------|---------|--------|
| Candidate is a substring of the correct answer (such as "Gehrig" vs "Lou Gehrig") | correct | Reasonable short form |
| Candidate contains the correct answer plus extra (such as "Lou Gehrig Jr." vs "Lou Gehrig") | incorrect | Adds wrong information |
| Candidate differs only in punctuation/articles | correct | Format variant |
| Context supports multiple possible answers and the candidate is one of them | correct | Evidence supported |
| Candidate is completely unrelated (entity from another domain) | incorrect | Clear mismatch |

---

## 6. Output Format

Output JSON:

```json
{
  "status": "correct or incorrect",
  "reason": "brief justification citing the evidence and the judgment logic"
}
```

---

## 7. Examples

### Example 1 (correct)
- **Question**: "Steven Tyler of this band lent his steamin' vocals to 'Train Kept A-Rollin'"
- **Candidate**: "Aerosmith"
- **Verdict**: correct
- **Reason**: the context explicitly mentions "Steve Tyler and Joe Perry at 2010 Aerosmith concert" and links Steven Tyler with Aerosmith in multiple places

### Example 2 (incorrect)
- **Question**: "Revolutionary War hero: 'His spirit is in Vermont now'"
- **Candidate**: "George Washington"
- **Verdict**: incorrect
- **Reason**: the context clearly points to "Ethan Allen" rather than George Washington, and Allen's link to Vermont is supported by multiple pieces of evidence
