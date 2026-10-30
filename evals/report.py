"""Turn eval rows into report.md: the settings, the metrics with 95% CIs, the per-bucket and per-rule tables, the failures and the cost.

Split out of run_evals.py to keep each file under about 200 lines (spec Section 1, rule 5).
"""

from evals import metrics
from officer import rules
from officer.diagnose import UNFINISHED_PREFIX


def categorise(row):
    """The failure category for one run, or None if the run matches its label."""
    if row["got_next_action"] in row["must_not"]:
        return "unsafe"
    if row["summary"].startswith(UNFINISHED_PREFIX):
        return "unfinished"
    if row["got_next_action"] != row["expected_next_action"]:
        return "wrong_action"
    if set(row["expected_stop_reasons"]) - set(row["got_stop_reasons"]):
        return "missed_fault"
    if set(row["got_stop_reasons"]) - set(row["expected_stop_reasons"]):
        return "invented_fault"
    return None


def _fmt_ci(ci):
    low, high = ci
    return "n/a" if low is None else f"[{low:.3f}, {high:.3f}]"


def _fmt(value):
    return "n/a" if value is None else f"{value:.3f}"


def _metric_rows(rows):
    """(name, value, 95% CI) for each headline metric. Each CI is a bootstrap over the run rows."""
    def micro(part):
        def statistic(sample):
            pairs = [(r["expected_stop_reasons"], r["got_stop_reasons"]) for r in sample]
            return metrics.micro_prf(pairs)[part]
        return statistic

    known = {rule["id"] for rule in rules.load_rules()}

    def non_existent(sample):
        return metrics.unknown_citation_rate(sample, known)

    def accuracy(sample):
        return metrics.accuracy([(r["expected_next_action"], r["got_next_action"]) for r in sample])

    specs = [
        ("Next-action accuracy", accuracy, accuracy(rows)),
        ("Stop-reason micro precision", micro("precision"), micro("precision")(rows)),
        ("Stop-reason micro recall", micro("recall"), micro("recall")(rows)),
        ("Stop-reason micro F1", micro("f1"), micro("f1")(rows)),
        ("Off-list citation rate (real rule, did not fail)", metrics.invented_citation_rate, metrics.invented_citation_rate(rows)),
        ("Non-existent rule rate (hallucinated ID)", non_existent, non_existent(rows)),
        ("Unsafe-action rate", metrics.unsafe_rate, metrics.unsafe_rate(rows)),
        ("Escalation recall", metrics.escalation_recall, metrics.escalation_recall(rows)),
        ("Consistency across runs", metrics.consistency, metrics.consistency(rows)),
        ("Completion rate (agent)", metrics.completion_rate, metrics.completion_rate(rows)),
        ("Tool error rate (agent)", metrics.tool_error_rate, metrics.tool_error_rate(rows)),
    ]
    # Intervals resample whole cases, so the k runs of one case stay together.
    return [(name, value, metrics.bootstrap_by_case(rows, statistic)) for name, statistic, value in specs]


def metrics_section(rows):
    """The metrics table, as Markdown. Also printed to the terminal."""
    lines = ["| Metric | Value | 95% CI |", "|---|---|---|"]
    for name, value, ci in _metric_rows(rows):
        lines.append(f"| {name} | {_fmt(value)} | {_fmt_ci(ci)} |")
    return "\n".join(lines)


def _bucket_table(rows):
    buckets = {}
    for row in rows:
        buckets.setdefault(row["bucket"], []).append(row)
    lines = ["| Bucket | Runs | Next-action accuracy |", "|---|---|---|"]
    for bucket, group in buckets.items():
        acc = metrics.accuracy([(r["expected_next_action"], r["got_next_action"]) for r in group])
        lines.append(f"| {bucket} | {len(group)} | {acc:.3f} |")
    return "\n".join(lines)


def _rule_table(rows):
    lines = ["| Stop reason | Recall |", "|---|---|"]
    for reason, recall in sorted(metrics.per_rule_recall(rows).items()):
        lines.append(f"| {reason} | {recall:.3f} |")
    return "\n".join(lines)


def _failure_table(rows):
    lines = ["| Case | Run | Expected | Got | Category |", "|---|---|---|---|---|"]
    failures = [(row, categorise(row)) for row in rows if categorise(row)]
    for row, category in failures:
        lines.append(
            f"| {row['case_id']} | {row['run']} | {row['expected_next_action']} "
            f"({', '.join(row['expected_stop_reasons']) or 'none'}) | {row['got_next_action']} "
            f"({', '.join(row['got_stop_reasons']) or 'none'}) | {category} |"
        )
    if not failures:
        lines.append("| none | | | | |")
    return "\n".join(lines)


def _cost_section(rows):
    total = sum(row["cost"] for row in rows)
    cases = len({row["case_id"] for row in rows})
    p50, p95 = metrics.latency_stats([row["seconds"] for row in rows])
    return "\n".join([
        f"- Total cost: ${total:.6f}",
        f"- Mean cost per case: ${total / cases:.6f}" if cases else "- Mean cost per case: n/a",
        f"- Calls: {sum(row['calls'] for row in rows)}, input tokens: {sum(row['input_tokens'] for row in rows)}, output tokens: {sum(row['output_tokens'] for row in rows)}",
        f"- Latency p50 {p50:.2f}s, p95 {p95:.2f}s",
    ])


def build_report(rows, settings):
    cases = len({row["case_id"] for row in rows})
    lines = [
        f"# Eval report: {settings['variant']} on {settings['split']}",
        "",
        "## Settings",
        f"- Variant: {settings['variant']}",
        f"- Split: {settings['split']}",
        f"- k: {settings['k']}",
        f"- Model: {settings['model']}",
        f"- Prompt version: {settings['prompt_version']}",
        f"- Date: {settings['date']}",
        f"- Cases: {cases}, runs: {len(rows)}",
        "",
        "## Metrics (95% bootstrap CIs, resampled by case)",
        metrics_section(rows),
        "",
    ]
    if cases < 30:
        lines += [f"With {cases} cases, differences inside overlapping CIs are not meaningful.", ""]
    lines += [
        "## Per-bucket accuracy",
        _bucket_table(rows),
        "",
        "## Per-stop-reason recall",
        _rule_table(rows),
        "",
        "## Failures",
        _failure_table(rows),
        "",
        "## Cost and latency",
        _cost_section(rows),
        "",
    ]
    return "\n".join(lines)


def _settings_from(folder):
    """Settings from settings.json, or from the Settings lines of an older report.md."""
    import json
    if (folder / "settings.json").exists():
        return json.loads((folder / "settings.json").read_text(encoding="utf-8"))
    keys = {"Variant": "variant", "Split": "split", "k": "k", "Model": "model", "Prompt version": "prompt_version", "Date": "date"}
    settings = {}
    for line in (folder / "report.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("- ") and ": " in line:
            label, value = line[2:].split(": ", 1)
            if label in keys:
                settings[keys[label]] = value
    return settings


def rebuild(folder):
    """Regenerate report.md from the saved rows. Used after a change to how metrics are reported."""
    import json
    rows = [json.loads(line) for line in (folder / "rows.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        # Older rows lack the agent fields. They are not agent runs, so these values are correct.
        row.setdefault("completed", None)
        row.setdefault("tool_calls", 0)
        row.setdefault("tool_errors", 0)
        row.setdefault("letters", [])
        # Rows written before the fix counted a scope-guard refusal as unfinished. It is a correct finish.
        if row["got_next_action"] == "refuse_out_of_scope" and row["completed"] is False:
            row["completed"] = True
    (folder / "report.md").write_text(build_report(rows, _settings_from(folder)), encoding="utf-8")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    for name in sys.argv[1:]:
        rebuild(Path(name))
        print(f"rebuilt {name}/report.md")
