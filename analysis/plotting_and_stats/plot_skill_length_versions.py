#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as font_manager

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "analysis"

BENCHMARKS = [
    ("BFCL-v4", ROOT / "evolved" / "bfcl-solver"),
    ("ALFWorld", ROOT / "evolved" / "alfworld-solver"),
    ("DocVQA", ROOT / "evolved" / "docvqa-solver"),
    ("LiveMath", ROOT / "evolved" / "livemath-solver"),
    ("SpreadsheetBench", ROOT / "evolved" / "spreadsheetbench-solver"),
]

COLORS = {
    "BFCL-v4": "#0072B2",
    "ALFWorld": "#D55E00",
    "DocVQA": "#009E73",
    "LiveMath": "#CC79A7",
    "SpreadsheetBench": "#E69F00",
}

MARKERS = {
    "BFCL-v4": "s",
    "ALFWorld": "o",
    "DocVQA": "D",
    "LiveMath": "^",
    "SpreadsheetBench": "P",
}

TOKEN_LABEL_OFFSETS = {
    "BFCL-v4": (6, 0),
    "ALFWorld": (6, -7),
    "DocVQA": (6, 1),
    "LiveMath": (6, 4),
    "SpreadsheetBench": (6, 0),
}

GROWTH_LABEL_OFFSETS = {
    "BFCL-v4": (6, 0),
    "ALFWorld": (6, 9),
    "DocVQA": (6, 0),
    "LiveMath": (6, -10),
    "SpreadsheetBench": (6, 0),
}

EXCLUDED_VERSION_PARTS = (
    "ablation",
    "bak",
    "conservative",
    "official",
    "oldharness",
    "plainVersion",
    "scrambled",
    "new",
)

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)

def load_tokenizer():
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return "cl100k_base", lambda text: len(encoding.encode(text))
    except Exception:
        return "regex_fallback", lambda text: len(TOKEN_PATTERN.findall(text))

def version_key(version_name: str) -> tuple[float, str]:
    match = re.fullmatch(r"v(\d+(?:\.\d+)?)", version_name)
    if not match:
        return (math.inf, version_name)
    return (float(match.group(1)), version_name)

def is_main_version(version_name: str) -> bool:
    if any(part in version_name for part in EXCLUDED_VERSION_PARTS):
        return False
    return re.fullmatch(r"v\d+(?:\.\d+)?", version_name) is not None

def collect_rows():
    tokenizer_name, count_tokens = load_tokenizer()
    rows = []

    for benchmark, skill_dir in BENCHMARKS:
        version_dirs = sorted(
            [path for path in skill_dir.glob("v*") if path.is_dir() and is_main_version(path.name)],
            key=lambda path: version_key(path.name),
        )
        baseline_tokens = None

        for version_dir in version_dirs:
            skill_path = version_dir / "SKILL.md"
            if not skill_path.exists():
                continue

            text = skill_path.read_text(encoding="utf-8")
            token_count = count_tokens(text)
            if baseline_tokens is None:
                baseline_tokens = token_count

            rows.append(
                {
                    "benchmark": benchmark,
                    "version": version_dir.name,
                    "version_num": version_key(version_dir.name)[0],
                    "token_count": token_count,
                    "delta_from_v0": token_count - baseline_tokens,
                    "growth_x": token_count / baseline_tokens if baseline_tokens else 1.0,
                    "line_count": text.count("\n") + 1,
                    "char_count": len(text),
                    "tokenizer": tokenizer_name,
                    "path": str(skill_path.relative_to(ROOT)),
                }
            )

    return rows

def write_csv(rows, output_path: Path):
    fieldnames = [
        "benchmark",
        "version",
        "version_num",
        "token_count",
        "delta_from_v0",
        "growth_x",
        "line_count",
        "char_count",
        "tokenizer",
        "path",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def setup_style():
    for font_path in [
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf",
    ]:
        try:
            font_manager.fontManager.addfont(font_path)
        except Exception:
            pass

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "font.size": 11,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.linewidth": 0.8,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.major.size": 3.5,
            "ytick.major.size": 3.5,
            "lines.linewidth": 1.9,
            "lines.markersize": 5.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.unicode_minus": False,
            "savefig.dpi": 300,
            "figure.dpi": 300,
        }
    )

def plot_lengths(rows, output_pdf: Path, output_png: Path):
    setup_style()
    fig, (ax_tokens, ax_growth) = plt.subplots(1, 2, figsize=(7.2, 3.0), sharex=False)

    for benchmark, _ in BENCHMARKS:
        series = [row for row in rows if row["benchmark"] == benchmark]
        if not series:
            continue

        x = [row["version_num"] for row in series]
        y_tokens = [row["token_count"] for row in series]
        y_growth = [row["growth_x"] for row in series]
        color = COLORS[benchmark]
        marker = MARKERS[benchmark]

        ax_tokens.plot(x, y_tokens, color=color, marker=marker, markeredgecolor="white", markeredgewidth=0.7)
        ax_growth.plot(x, y_growth, color=color, marker=marker, markeredgecolor="white", markeredgewidth=0.7)

        token_offset = TOKEN_LABEL_OFFSETS[benchmark]
        growth_offset = GROWTH_LABEL_OFFSETS[benchmark]
        ax_tokens.annotate(
            benchmark,
            xy=(x[-1], y_tokens[-1]),
            xytext=token_offset,
            textcoords="offset points",
            color=color,
            fontsize=9,
            va="center",
            clip_on=False,
        )
        ax_growth.annotate(
            benchmark,
            xy=(x[-1], y_growth[-1]),
            xytext=growth_offset,
            textcoords="offset points",
            color=color,
            fontsize=9,
            va="center",
            clip_on=False,
        )

    for ax in (ax_tokens, ax_growth):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, linestyle="-", alpha=0.18, zorder=0)
        ax.set_xlabel("Skill Version")
        ax.set_xticks([0, 1, 2, 3, 4, 5])
        ax.set_xlim(-0.15, 5.85)

    ax_tokens.set_ylabel("Skill Length (tokens)")
    ax_growth.set_ylabel("Growth vs. v0 ($\\times$)")
    ax_growth.axhline(1.0, color="#333333", linewidth=0.7, linestyle=":", zorder=1)

    max_tokens = max(row["token_count"] for row in rows)
    max_growth = max(row["growth_x"] for row in rows)
    ax_tokens.set_ylim(0, max_tokens * 1.12)
    ax_growth.set_ylim(0.8, max_growth * 1.12)

    fig.tight_layout(pad=0.5, w_pad=1.6)
    fig.savefig(output_pdf, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(output_png, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

def print_summary(rows):
    tokenizer = rows[0]["tokenizer"] if rows else "unknown"
    print(f"Tokenizer: {tokenizer}")
    print("benchmark,versions,v0_tokens,final_tokens,delta,growth_x")
    for benchmark, _ in BENCHMARKS:
        series = [row for row in rows if row["benchmark"] == benchmark]
        if not series:
            continue
        first = series[0]
        last = series[-1]
        versions = "->".join(row["version"] for row in series)
        print(
            f"{benchmark},{versions},{first['token_count']},{last['token_count']},"
            f"{last['delta_from_v0']},{last['growth_x']:.2f}"
        )

def main():
    rows = collect_rows()
    csv_path = OUTPUT_DIR / "skill_length_by_version.csv"
    pdf_path = OUTPUT_DIR / "figure_skill_length_by_version.pdf"
    png_path = OUTPUT_DIR / "figure_skill_length_by_version.png"

    write_csv(rows, csv_path)
    plot_lengths(rows, pdf_path, png_path)
    print_summary(rows)
    print(f"Saved: {csv_path}")
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")

if __name__ == "__main__":
    main()
