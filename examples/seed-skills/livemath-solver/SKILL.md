---
type: task_skill
task_name: LiveMath theorem multiple-choice solving
description: Solve theorem-grounded advanced math multiple-choice questions by precisely comparing quantifiers, hypotheses, equality conditions, and extremal cases across option wordings, and pick the unique correct mathematical statement
current_version: v0
parent_version: null
repair_brief: null
evolution_note: "Seed version, ported from the reference implementation and adapted to this framework format"
---

# Task Skill: LiveMath Theorem-Grounded Math MCQ

## 1. Definition and Scope

**Task definition**: given an advanced math multiple-choice question (stem plus options A/B/C/D), each option is a mathematical statement (theorem conclusion, inequality, characterization). **Exactly one** option is the correct statement supported by the stem, and the rest are distractors. Select the unique correct option label.

**Scoring**: Exact Match. The final chosen option label (such as A) is compared character by character with the correct label. Only an exact match earns 1 point. **Only the final chosen label matters, the process is not scored.**

**Core principle**: reason rigorously from the **hypotheses, domain, quantifiers, and conclusion form** given in the stem. Distractors are usually **subtle tampering** of the correct statement (weakening, strengthening, quantifier change, dropped equality, changed domain) and must be examined one by one before locking the answer.

---

## 2. Option Comparison Discipline

1. **Compare all options side by side**: read all options fully before answering. Never commit at the first option that "looks right". The correct option is usually **the strongest statement the stem can support that still holds exactly**, while nearby distractors are its weakened version, over-strong version, or a version missing an equality or boundary case.
2. **Lock quantifier differences**: track "there exists / for every / if and only if / exactly when / unique" precisely. Distractors often swap "exists" with "for all", or weaken "if and only if" into a one-way implication.
3. **Pairwise contrast**: when two options are worded very similarly, compare them sentence by sentence and find the **single wording difference** (a constant dependency, an inequality direction, an interval endpoint), then judge which one matches the stem hypotheses.

---

## 3. Theorem-Level Precision

1. **Check weakening**: whether an option drops a characterization, an equality case, or a full equivalence, downgrading "necessary and sufficient" to merely "sufficient".
2. **Check over-strengthening**: whether an option raises regularity, removes a scale restriction, upgrades "existence" to "for all", or turns a local conclusion into a global one.
3. **Constants and dependencies**: watch the dependency of constants on parameters (for example whether \(C\) depends on \(T\), on the initial data, or is universal). Distractors often forge errors by tampering with dependencies.

---

## 4. Hypothesis and Domain Verification

1. **Verify hypotheses**: carefully check the hypotheses, domain, and parameter ranges given by the stem. Distractors often keep the overall theorem shape but **quietly alter the required hypotheses** (such as changing \(\gamma\in[1,8/3)\) into \(\gamma\in[1,\infty)\)).
2. **Equality and extremal cases**: watch equality conditions, extremal conditions, and whether the conclusion applies to **the whole family** or only a **restricted subfamily**.
3. **Boundary endpoints**: open versus closed interval endpoints and dimension conditions (\(N=2\) vs \(N=3\)) are frequent tampering points.

---

## 5. Answering Workflow (SOP)

### Step 1: Parse the stem
- Extract **all hypotheses** given in the stem (parameter ranges, domain, initial conditions, dimension conventions).
- Identify what kind of conclusion is being asked (existence / uniqueness / estimate / characterization / equivalence).

### Step 2: Annotate each option
- For each option, annotate its **assertion form** relative to the stem (quantifiers, equivalence strength, constant dependency, domain).
- Record in one sentence the **difference** between each option and "the statement directly supported by the stem".

### Step 3: Eliminate distractors
- Eliminate one by one: weakened (dropped equality/characterization), over-strong (raised regularity/quantifier), hypothesis-tampered (changed interval/dimension/dependency).
- If several candidates remain, return to Step 2 for pairwise contrast and lock the single difference.

### Step 4: Lock and self-check
- Confirm the chosen option is **neither weaker nor stronger** than what the stem supports, and that hypotheses, quantifiers, equalities, and dependencies all match.
- Self-check: was I misled by an over-strong option that looks "more complete"? Did I miss a key qualifier in some option?

---

## 6. Common Failures and Avoidance

| Failure type | Description | Avoidance |
|--------------|-------------|-----------|
| quantifier_slip | Confused exists/for-all or sufficient/iff | Annotate each quantifier and contrast pairwise |
| over_strong | Picked an option with raised regularity or upgraded to global/universal | Check whether the stem hypotheses truly support such strength |
| missing_equality | Picked a weakened version missing the equality case or full characterization | Prefer the strongest statement the stem supports that still holds exactly |
| hypothesis_tamper | Ignored altered intervals/dimensions/dependencies in an option | Verify each option's hypotheses against the stem item by item |
| premature_commit | Committed at the first plausible option | Force a full side-by-side comparison before deciding |

---

## 7. Output Format

After step-by-step reasoning, put the final answer inside `<answer>...</answer>`, containing **only the single option label** (such as A or C), without explanation, period, or any other characters.

Examples:
- `<answer>B</answer>`
- `<answer>A</answer>`
