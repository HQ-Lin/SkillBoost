"""Repository-local adapter for the official BFCL evaluator package.

The adapter deliberately performs imports lazily.  This keeps ``--help`` and static
inspection available without the optional BFCL dependency, while real evaluations use
the runtime and benchmark assets distributed by the pinned ``bfcl-eval`` package.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class BfclRuntime:
    data_dir: Path
    multi_turn_checker: Callable
    execute_multi_turn_func_call: Callable
    is_empty_execute_response: Callable


def load_bfcl_runtime(data_dir: str | Path | None = None) -> BfclRuntime:
    """Load BFCL code and resolve its packaged data without a source checkout."""
    try:
        import bfcl_eval
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import (
            multi_turn_checker,
        )
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
            execute_multi_turn_func_call,
            is_empty_execute_response,
        )
    except ImportError as exc:
        raise RuntimeError(
            "BFCL support is not installed. Run: python3 -m pip install -e '.[bfcl]'"
        ) from exc

    resolved_data_dir = (
        Path(data_dir).expanduser().resolve()
        if data_dir
        else Path(bfcl_eval.__file__).resolve().parent / "data"
    )
    required = (
        resolved_data_dir / "multi_turn_func_doc",
        resolved_data_dir / "possible_answer",
    )
    missing = [str(path) for path in required if not path.is_dir()]
    if missing:
        raise RuntimeError(
            "Invalid BFCL data directory; missing required paths: " + ", ".join(missing)
        )

    return BfclRuntime(
        data_dir=resolved_data_dir,
        multi_turn_checker=multi_turn_checker,
        execute_multi_turn_func_call=execute_multi_turn_func_call,
        is_empty_execute_response=is_empty_execute_response,
    )
