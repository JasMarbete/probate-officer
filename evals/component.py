"""Component evaluation (M7): each judgement rule on its own, against labels from the generator's faults.

A judgement rule should fail on a case exactly when the generator put in its fault.
The judgement rules with no fault in the generator (R-WILL-06, R-NAME-01) should always pass.
Each judgement check is one model call, so this run asks before it starts.
"""

import json
from collections import defaultdict
from datetime import datetime

import config
from officer.checks import rules
from officer.intake import store
from officer.judgement import judge_rules
from evals import run_evals


def component_rows(labels):
    """One row per (case, judgement rule): what the label says, and what the judge said."""
    rows = []
    for label in labels:
        store.reset_case(label["case_id"])
        case = store.load_case(label["case_id"])
        findings = {finding.rule_id: finding for finding in judge_rules.run_judgement(case)}
        for rule in rules.judgement_rules_for(case):
            expected_fail = rule["on_fail"]["stop_reason"] in label["stop_reasons"]
            got_fail = not findings[rule["id"]].passed
            rows.append({
                "case_id": label["case_id"],
                "rule_id": rule["id"],
                "expected_fail": expected_fail,
                "got_fail": got_fail,
                "correct": expected_fail == got_fail,
            })
    return rows


def accuracy_by_rule(rows):
    """{rule_id: (correct, total)}."""
    tally = defaultdict(lambda: [0, 0])
    for row in rows:
        tally[row["rule_id"]][1] += 1
        tally[row["rule_id"]][0] += row["correct"]
    return {rule_id: tuple(counts) for rule_id, counts in sorted(tally.items())}


def _component_report(rows, split):
    lines = [
        f"# Component report: judgement rules on {split}",
        "",
        f"Cases: {len({row['case_id'] for row in rows})}, judge calls: {len(rows)}",
        "",
        "| Rule | Correct | Total | Accuracy |",
        "|---|---|---|---|",
    ]
    for rule_id, (correct, total) in accuracy_by_rule(rows).items():
        lines.append(f"| {rule_id} | {correct} | {total} | {correct / total:.3f} |")
    return "\n".join(lines) + "\n"


def main(split, assume_yes):
    labels = run_evals.load_expected(split)
    # Count the calls from the rules that apply, so the estimate is exact.
    calls = 0
    for label in labels:
        store.reset_case(label["case_id"])
        calls += len(rules.judgement_rules_for(store.load_case(label["case_id"])))
    if not run_evals.confirm(calls, assume_yes):
        print("Not run.")
        return 1

    rows = component_rows(labels)
    folder = config.RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}_component_{split}"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    text = _component_report(rows, split)
    (folder / "component.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {folder / 'component.md'}")
    return 0
