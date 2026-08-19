import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

                                                

def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def load_results(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def load_trace(trace_path: Path) -> dict | None:
    if not trace_path.exists():
        return None
    try:
        return json.loads(trace_path.read_text(encoding="utf-8"))
    except Exception:
        return None

def find_traces_dir(report_path: Path) -> Path | None:
    run_dir = report_path.parent
    traces_dir = run_dir / "traces"
    if traces_dir.exists():
        return traces_dir
    parent_traces = run_dir.parent / "traces"
    if parent_traces.exists():
        return parent_traces
    return None

                                                

def classify_failure(result: dict) -> dict:
    """for single  itemsfailed case  linesclass. """
    expected = set(result.get("expected_methods", []))
    called = set(result.get("called_methods", []))

    missed = sorted(expected - called)
    extra = sorted(called - expected)
    hit = sorted(expected & called)

    if not called:
        failure_type = "empty"
    elif not missed:
        failure_type = "pass"
    elif not hit:
        failure_type = "total_miss"
    else:
        failure_type = "partial_miss"

    return {
        "failure_type": failure_type,
        "missed_functions": missed,
        "extra_functions": extra,
        "hit_functions": hit,
        "recall": result.get("recall", 0),
        "n_expected": len(expected),
        "n_called": len(called),
    }

def cluster_by_category(results: list[dict]) -> dict[str, list[dict]]:
    clusters = defaultdict(list)
    for r in results:
        cat = r.get("category", "unknown")
        clusters[cat].append(r)
    return dict(clusters)

def cluster_by_missed_function(fail_cases: list[dict]) -> dict[str, list[str]]:
    """by missed function countnameclusterclass. """
    clusters = defaultdict(list)
    for r in fail_cases:
        info = classify_failure(r)
        for fn in info["missed_functions"]:
            clusters[fn].append(r.get("id", "?"))
    return dict(sorted(clusters.items(), key=lambda x: -len(x[1])))

def cluster_by_failure_type(fail_cases: list[dict]) -> dict[str, list[str]]:
    """by failedclasstypeclusterclass. """
    clusters = defaultdict(list)
    for r in fail_cases:
        info = classify_failure(r)
        clusters[info["failure_type"]].append(r.get("id", "?"))
    return dict(clusters)

                                                    

def extract_trace_summary(trace: dict, max_chars: int = 800) -> str:
    """from  BFCL trace  in extractkeyinfosummaryrequire . """
    if not trace:
        return ""

    parts = []

    expected = trace.get("expected_methods", [])
    called = trace.get("called_methods", [])
    parts.append(f"expectedcall: {expected}")
    parts.append(f"actualcall: {called}")

    missed = set(expected) - set(called)
    extra = set(called) - set(expected)
    if missed:
        parts.append(f"missed function count: {sorted(missed)}")
    if extra:
        parts.append(f"redundant function count: {sorted(extra)}")

    turns = trace.get("turns", [])
    for t in turns:
        turn_idx = t.get("turn", "?")
        calls = t.get("calls", [])
        if calls:
            call_names = [c.get("name", "?") for c in calls]
            parts.append(f"Turn {turn_idx}: call {call_names}")
        else:
            parts.append(f"Turn {turn_idx}: no call")

    summary = "\n".join(parts)
    return summary[:max_chars]

                                                

def find_version_history(report_path: Path) -> list[dict]:
    """at  evals directoryfind history report. """
    evals_dir = report_path.parent
    if evals_dir.name != "evals":
        parent_evals = report_path.parent.parent
        if parent_evals.name == "evals":
            evals_dir = parent_evals
        else:
            evals_dir = report_path.parent

    evolved_root = evals_dir
    while evolved_root.name not in ("evals", "") and not (evolved_root / "v0").exists():
        evolved_root = evolved_root.parent
    if (evolved_root / "v0").exists():
        pass
    else:
        evolved_root = evals_dir.parent

    history = []
    evals_root = evolved_root / "evals"
    if not evals_root.exists():
        evals_root = evolved_root

    for run_dir in sorted(evals_root.glob("run_*")):
        report_file = run_dir / "report.json"
        if report_file.exists() and report_file != report_path:
            try:
                r = json.loads(report_file.read_text(encoding="utf-8"))
                history.append({
                    "run_id": r.get("run_id", run_dir.name),
                    "model": r.get("model", "?"),
                    "pass_rate": r.get("pass_rate", 0),
                    "func_name_recall": r.get("func_name_recall", 0),
                    "empty_rate": r.get("empty_rate", 0),
                    "total": r.get("total", 0),
                    "passed": r.get("passed", 0),
                })
            except Exception:
                pass
    return history

                                                 

def format_context(
    report: dict,
    results: list[dict],
    traces: dict[str, dict],
    skill_path: Path,
    history: list[dict],
) -> str:
    lines = []

           
    run_id = report.get("run_id", "?")
    model = report.get("model", "?")
    lines.append(f"# BFCL attribution context: {run_id}")
    lines.append(f"\n## ")
    lines.append(f"- Skill: `{skill_path}`")
    lines.append(f"- model: {model}")
    lines.append(f"- total case: {report.get('total', 0)}")
    lines.append(f"- pass rate (pass_rate): {report.get('pass_rate', 0):.2f}%")
    lines.append(f"- function countname (func_name_recall): {report.get('func_name_recall', 0):.2f}%")
    lines.append(f"- empty rate (empty_rate): {report.get('empty_rate', 0):.2f}%")
    lines.append(f"- passed: {report.get('passed', 0)} / {report.get('total', 0)}")

              
    by_cat = report.get("by_category", {})
    if by_cat:
        lines.append(f"\n### classlabel")
        lines.append("| class |  count | pass_rate | recall |")
        lines.append("|------|------|-----------|--------|")
        for cat, stats in sorted(by_cat.items()):
            lines.append(f"| {cat} | {stats.get('n', 0)} | {stats.get('pass_rate', 0):.1f}% | {stats.get('recall', 0):.1f}% |")

                   
    fail_cases = [r for r in results if not r.get("passed", False)]
    pass_cases = [r for r in results if r.get("passed", False)]

    lines.append(f"\n---\n## failedsummaryrequire ")
    lines.append(f"- failed case: {len(fail_cases)}  items")
    lines.append(f"- passed case: {len(pass_cases)}  items")

                
    type_clusters = cluster_by_failure_type(fail_cases)
    if type_clusters:
        lines.append(f"\n### by failedclasstypeclusterclass")
        for ftype, ids in type_clusters.items():
            lines.append(f"- **{ftype}** ({len(ids)} items): {ids}")

                
    fn_clusters = cluster_by_missed_function(fail_cases)
    if fn_clusters:
        lines.append(f"\n### by missed function countclusterclass (Top )")
        for fn, ids in list(fn_clusters.items())[:15]:
            lines.append(f"- **{fn}** ({len(ids)} items case missed): {ids}")

                      
    cat_clusters = cluster_by_category(fail_cases)
    if cat_clusters:
        lines.append(f"\n### by  category clusterclass")
        for cat, cases in sorted(cat_clusters.items()):
            ids = [c.get("id", "?") for c in cases]
            lines.append(f"- **{cat}** ({len(cases)} items): {ids}")

                             
    lines.append(f"\n---\n## per  Case detail (failed case) ")
    lines.append("")
    lines.append("| # | case_id | category | failedclasstype | recall | expectedfunction count | actualcall | missed function count | redundant function count |")
    lines.append("|---|---------|----------|---------|--------|---------|---------|---------|---------|")

    for i, r in enumerate(fail_cases, 1):
        info = classify_failure(r)
        case_id = r.get("id", "?")
        cat = r.get("category", "?")
        lines.append(
            f"| {i} | `{case_id}` | {cat} | {info['failure_type']} | "
            f"{info['recall']:.2f} | {info['n_expected']} | {info['n_called']} | "
            f"{info['missed_functions']} | {info['extra_functions']} |"
        )

                 
    if traces:
        lines.append(f"\n---\n## Trace  (failed case) ")
        for r in fail_cases:
            case_id = r.get("id", "?")
            trace_key = f"trace_{case_id}"
            trace = traces.get(trace_key) or traces.get(case_id)
            if not trace:
                continue

            info = classify_failure(r)
            lines.append(f"\n### [{info['failure_type']}] {case_id}")
            lines.append(f"- Category: {r.get('category', '?')}")
            lines.append(f"- Recall: {r.get('recall', 0):.2f}")
            lines.append(f"- expected: {r.get('expected_methods', [])}")
            lines.append(f"- actual: {r.get('called_methods', [])}")

            summary = extract_trace_summary(trace)
            if summary:
                lines.append(f"\n<details><summary>Trace summaryrequire </summary>\n")
                lines.append(f"```\n{summary}\n```\n")
                lines.append("</details>")

             
    if history:
        lines.append(f"\n---\n## versiontrend")
        for h in history[-10:]:
            lines.append(
                f"- {h['run_id']}: pass_rate={h['pass_rate']:.2f}% "
                f"recall={h['func_name_recall']:.2f}% "
                f"({h['passed']}/{h['total']})"
            )
    lines.append(
        f"- **when top  ({run_id}) **: pass_rate={report.get('pass_rate', 0):.2f}% "
        f"recall={report.get('func_name_recall', 0):.2f}% "
        f"({report.get('passed', 0)}/{report.get('total', 0)})"
    )

    return "\n".join(lines)

                                               

def main():
    parser = argparse.ArgumentParser(
        description="BFCL multi-turn function calling evaluationattributiondataprepare tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
not call LLM, only dataprepare . produceattribution context Agent (Claude) consumption.

show example:
    python3 analysis/eval_analysis/bfcl_analyze.py \\
        evolved/bfcl-solver/evals/run_v0_baseline_20260606_120000/report.json \\
        evolved/bfcl-solver/evals/run_v0_baseline_20260606_120000/results.jsonl \\
        evolved/bfcl-solver/v0/SKILL.md \\
        --output evolved/bfcl-solver/mutation_briefs/context_v0.md
""")
    parser.add_argument("report", help="report.json path")
    parser.add_argument("results", help="results.jsonl path")
    parser.add_argument("skill_md", help="vN/SKILL.md path")
    parser.add_argument("--traces-dir", help="traces/ directory (defaultauto-inferred)")
    parser.add_argument("--output", "-o", help="outputfilepath (default stdout) ")
    args = parser.parse_args()

    report_path = Path(args.report)
    results_path = Path(args.results)
    skill_path = Path(args.skill_md)

    for p, label in [(report_path, "report"), (results_path, "results"), (skill_path, "skill")]:
        if not p.exists():
            print(f"[ERROR] {label} file not found: {p}", file=sys.stderr)
            sys.exit(1)

    report = load_report(report_path)
    results = load_results(results_path)

               
    traces_dir = Path(args.traces_dir) if args.traces_dir else find_traces_dir(report_path)
    traces = {}
    if traces_dir and traces_dir.exists():
        for tf in traces_dir.glob("trace_*.json"):
            t = load_trace(tf)
            if t:
                traces[tf.stem] = t

    history = find_version_history(report_path)

    context = format_context(report, results, traces, skill_path, history)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(context, encoding="utf-8")
        print(f"[Done] attribution context saved to {out}", file=sys.stderr)
    else:
        print(context)

if __name__ == "__main__":
    main()
