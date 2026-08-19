---
type: task_skill
task_name: SWE-bench code repair
description: Given a GitHub issue description and relevant code context, generate a standard unified diff patch that fixes the issue
current_version: v0
parent_version: null
repair_brief: null
evolution_note: "Seed version, designed from SWE-bench best practices"
---

# Task Skill: SWE-bench Code Repair (Issue-to-Patch)

## 1. Task Definition and Scope

**Input**:
- `problem_statement`: GitHub issue description (error symptoms, stack traces, reproduction steps, expected behavior).
- `hints_text` (optional): hints from maintainers or the community, possibly pointing to relevant files, functions, or the root cause.
- `repo` info: repository structure, target source file contents, related context.

**Output**: a standard unified diff patch that can be applied directly with `git apply` to the target repository.

**Evaluation criteria**:
- After applying the patch, **fail-to-pass** tests flip from failing to passing (the fix actually solves the issue).
- **pass-to-pass** tests keep passing with no regression.
- The patch format is valid and applies cleanly with `git apply`.

---

## 2. Core Principles

1. **Minimal change**: modify only the code required to fix the issue, never touch unrelated lines or files.
2. **Format correctness**: the output must be a valid unified diff with proper file headers, hunk headers, and prefix symbols.
3. **No regression**: existing (pass-to-pass) tests must keep passing and existing behavior must not break.
4. **Precise localization**: locate the exact file and code position to modify, never patch the wrong place.
5. **Understand first**: identify the root cause before designing the fix, avoid superficial symptom masking.

---

## 3. Patch Generation SOP

### Step 1: Parse the problem statement
- Extract key information from `problem_statement`: **error symptoms**, **stack trace/exception type**, **reproduction steps**, **expected behavior**.
- Distinguish "the symptom the user sees" from "the correct behavior the code should have".

### Step 2: Locate the relevant code
- Use file names, function names, and line numbers in the error message plus clues from `hints_text` to locate the files and functions to modify.
- Read the full context of the relevant functions and confirm call relationships and data flow.

### Step 3: Analyze the root cause
- Explain **why the current code produces the wrong behavior**: unhandled boundary condition, wrong logical check, type mismatch, or state management issue.
- Confirm the root cause rather than the surface symptom, avoiding fixes that merely silence the error.

### Step 4: Design the fix
- Design the **minimal change** that avoids side effects and keeps pass-to-pass tests green.
- Consider generality: the fix should cover the same class of edge cases, not just the specific input in the report.

### Step 5: Generate the unified diff patch
- Produce the patch strictly in unified diff format, keeping file headers, hunk header line numbers, and context lines consistent with the actual repository code.

### Step 6: Self-check
- **Format validity**: complete file/hunk headers, correct line-number math, proper prefix symbols.
- **Logical completeness**: does the fix truly address the root cause and cover the expected behavior.
- **Edge cases**: any missed general cases, boundary values, or null/exception branches.
- **Context match**: context lines must match the actual code character by character so `git apply` succeeds.

---

## 4. Unified Diff Format Rules

A valid unified diff consists of:

- **File headers**: identify the modified file, old version starts with `--- a/`, new version with `+++ b/`.
  ```
  --- a/path/to/file.py
  +++ b/path/to/file.py
  ```
- **Hunk header**: marks the position and range of a change, in the form `@@ -start,count +start,count @@`.
  - `-start,count`: starting line and line count of the hunk in the old file.
  - `+start,count`: starting line and line count of the hunk in the new file.
- **Line prefixes**:
  - `-` prefix: deleted line.
  - `+` prefix: added line.
  - ` ` (space) prefix: unchanged context line (used for anchoring, must match the original file character by character).

**Few-shot example** (adding division-by-zero protection to `divide`):

```
--- a/calculator/ops.py
+++ b/calculator/ops.py
@@ -10,7 +10,9 @@ def multiply(a, b):
     return a * b
 
 
 def divide(a, b):
-    return a / b
+    if b == 0:
+        raise ValueError("division by zero is not allowed")
+    return a / b
 
 
 def power(a, b):
```

---

## 5. Common Failures and Avoidance

| Failure type | Description | Avoidance |
|--------------|-------------|-----------|
| Format error | Missing file headers, wrong hunk line-number math, mixed tabs/spaces | Verify file and hunk headers strictly, keep the same indentation characters as the original file |
| Over-editing | Refactoring unrelated code, adding unnecessary logs/comments, touching unrelated lines | Stick to the minimal change, keep only the lines required by the fix |
| Missed edge cases | Handling only the specific reported case, missing the general fix | Cover the same class of boundaries and exception branches from the root cause |
| Wrong path | File path inconsistent with the actual repository layout | Use the real repository path in the `a/` and `b/` headers |
| Wrong context lines | Context lines mismatch the actual code so the patch fails to apply | Copy context lines verbatim, align line numbers and indentation exactly |

---

## 6. Output Format

- The output must be **pure unified diff content**, with **no explanatory text, markdown code fences (```), or JSON wrapping**.
- Start with `---` (the first file header) and end with the last modified line.
- If multiple files need changes, output each file's diff in sequence (each starting with its own `--- a/...` / `+++ b/...` headers).

Example (the output content itself, without any wrapper):

```
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,7 +10,9 @@ def divide(a, b):
-    return a / b
+    if b == 0:
+        raise ValueError("division by zero is not allowed")
+    return a / b
```
