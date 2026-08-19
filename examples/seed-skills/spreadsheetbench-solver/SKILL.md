---
name: spreadsheetbench-solver
description: Guides the LLM to manipulate Excel (.xlsx) spreadsheets by writing Python code (openpyxl / pandas) for SpreadsheetBench tasks. Emphasizes computing formula values in Python and writing static values into cells, then saving and reading back for verification, to avoid writing formula strings that the evaluator reads as None.
---

# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Use only the standard library, `openpyxl`, and `pandas`. Never use any other third-party libraries.

---

## Critical Rules (MUST follow)

1. **NEVER write Excel formulas to cells that will be graded on their displayed value.**
   `openpyxl` does NOT compute formulas — when the workbook is reopened with `data_only=True`
   (which is exactly how the evaluator reads it), a formula cell reads back as `None` and the
   answer is marked WRONG.
   **Instead, compute the result in Python and write the literal value** (number / string / datetime).
   - Wrong: `ws["D2"] = "=SUM(A2:C2)"`
   - Right: `ws["D2"] = a2 + b2 + c2`  (compute in Python, write the number)

2. **After saving, reopen and verify the written values** to make sure they are concrete values,
   not formulas or `None`:
   ```python
   wb2 = openpyxl.load_workbook(OUTPUT_PATH, data_only=True)
   print(wb2["Sheet1"]["D2"].value)  # must be a value, never None or a "=..." string
   ```

3. **Match value types to what the grader expects.** Numeric answers should be written as
   `int`/`float` (not strings); date/time answers should use proper Python `datetime` objects
   so openpyxl stores them as real Excel values.

---

## Common Workflow

1. **Explore** the input file: list sheets, inspect headers, check dimensions.
2. **Write the script** with `INPUT_PATH` and `OUTPUT_PATH` already provided as variables.
3. **Compute** the requested result in Python (do not delegate the math to Excel formulas).
4. **Save** to `OUTPUT_PATH`, then **reopen and confirm** the target cells contain concrete values.

---

## Library Selection

| Use case | Library |
|----------|---------|
| Preserve formulas, formatting, named ranges | `openpyxl` |
| Bulk data transformation, aggregation, sorting | `pandas` → write back with `openpyxl` |
| Simple cell read/write | `openpyxl` |

**Warning**: `pandas.to_excel()` silently destroys existing formulas and named ranges.
When writing back to a spreadsheet that must preserve unrelated cells, prefer `openpyxl`.

---

## solution.py Template

```python
import openpyxl
import pandas as pd  # optional

# INPUT_PATH and OUTPUT_PATH are provided by the harness.
wb = openpyxl.load_workbook(INPUT_PATH)
ws = wb.active  # or wb["SheetName"]

# --- compute results in Python and write LITERAL values (never formulas) ---
# e.g. ws["D2"] = round(total, 2)

wb.save(OUTPUT_PATH)
```

---

## Output Requirements

- Save the result to `OUTPUT_PATH`.
- Write computed literal values, never Excel formula strings, to graded cells.
- Do not hardcode row counts or column letters — iterate over actual rows in the workbook;
  the preview may be truncated, so do not assume data ends at the last previewed row.
- Preserve sheets and cells not mentioned in the instruction.
- Do not print prompts, do not call `input()`, do not hardcode file paths.
