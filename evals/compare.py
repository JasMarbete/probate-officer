"""Merge the latest test-split run of each variant into one ablation table and a failure analysis.

Usage: python -m evals.compare
Writes evals/results/ablation.md and evals/results/failure_analysis.md.
"""

import json
import sys
from collections import Counter

import config
from evals import report

VARIANTS = ["rules", "diagnose", "agent", "agent_write", "llm_only", "baseline"]


def latest_run(variant, split="test"):
    folders = sorted(config.RESULTS_DIR.glob(f"*_{variant}_{split}"))
    return folders[-1] if folders else None


def load_rows(folder):
    with (folder / "rows.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _fmt_ci(value, ci):
    if value is None:
        return "n/a"
    low, high = ci
    return f"{value:.3f} [{low:.3f}, {high:.3f}]" if low is not None else f"{value:.3f}"


def ablation_table(runs):
    names = [name for name, _, _ in report._metric_rows(next(iter(runs.values())))]
    header = "| Metric | " + " | ".join(runs) + " |"
    lines = [header, "|---|" + "---|" * len(runs)]
    columns = {variant: report._metric_rows(rows) for variant, rows in runs.items()}
    for index, name in enumerate(names):
        cells = [_fmt_ci(columns[v][index][1], columns[v][index][2]) for v in runs]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    cost = ["$%.6f per case" % (sum(r["cost"] for r in rows) / len({r["case_id"] for r in rows})) for rows in runs.values()]
    lines.append("| Mean cost per case | " + " | ".join(cost) + " |")
    return "\n".join(lines)


def failure_analysis(runs):
    counts = Counter()
    examples = {}
    for variant, rows in runs.items():
        for row in rows:
            category = report.categorise(row)
            if category is None:
                continue
            counts[category] += 1
            examples.setdefault(category, (variant, row))
    lines = ["# Failure analysis (test split)", "", "| Category | Runs |", "|---|---|"]
    for category, count in counts.most_common():
        lines.append(f"| {category} | {count} |")
    lines += ["", "## Top three categories, one example each", ""]
    for category, count in counts.most_common(3):
        variant, row = examples[category]
        lines.append(
            f"- **{category}** ({count} runs). Example: `{row['case_id']}` on `{variant}`. "
            f"Expected {row['expected_next_action']} ({', '.join(row['expected_stop_reasons']) or 'none'}); "
            f"got {row['got_next_action']} ({', '.join(row['got_stop_reasons']) or 'none'}). "
            f"Summary: {row['summary'][:200]}"
        )
    if not counts:
        lines.append("No failures in any variant.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    runs = {}
    for variant in VARIANTS:
        folder = latest_run(variant)
        if folder is None:
            print(f"skipping {variant}: no test-split run found")
            continue
        runs[variant] = load_rows(folder)
    if not runs:
        print("No test-split runs found.")
        return 1
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / "ablation.md").write_text("# Ablation (test split, latest run per variant)\n\n" + ablation_table(runs) + "\n", encoding="utf-8")
    (config.RESULTS_DIR / "failure_analysis.md").write_text(failure_analysis(runs), encoding="utf-8")
    print(ablation_table(runs))
    print(f"\nWrote {config.RESULTS_DIR / 'ablation.md'} and failure_analysis.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
