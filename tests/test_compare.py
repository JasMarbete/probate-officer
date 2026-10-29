"""Tests for evals/compare.py: the ablation table and the failure analysis, built from saved rows."""

from evals import compare


def _row(case_id, got="stop_case", expected="stop_case", **extra):
    row = {
        "case_id": case_id, "bucket": "single_fault",
        "expected_next_action": expected, "got_next_action": got,
        "expected_stop_reasons": ["DEATH_CERT_MISSING"], "got_stop_reasons": ["DEATH_CERT_MISSING"],
        "must_not": ["route_to_examiner"], "rules_cited": ["R-DOC-01"], "allowed_rules": ["R-DOC-01"],
        "proposal_actions": [], "summary": "ok", "completed": None, "tool_calls": 0, "tool_errors": 0,
        "cost": 0.001, "seconds": 1.0,
    }
    row.update(extra)
    return row


def test_ablation_table_has_one_column_per_variant_and_a_cost_row():
    runs = {"rules": [_row("A"), _row("B")], "agent": [_row("A"), _row("B", got="escalate")]}
    table = compare.ablation_table(runs)
    assert table.splitlines()[0] == "| Metric | rules | agent |"
    assert "| Next-action accuracy | 1.000" in table
    assert "Mean cost per case" in table


def test_failure_analysis_ranks_categories_and_gives_an_example():
    runs = {"agent": [_row("A", got="escalate"), _row("B", got="escalate"), _row("C", got="route_to_examiner")]}
    text = compare.failure_analysis(runs)
    assert "| wrong_action | 2 |" in text and "| unsafe | 1 |" in text
    assert "Example: `A` on `agent`" in text


def test_failure_analysis_with_no_failures_says_so():
    assert "No failures in any variant." in compare.failure_analysis({"rules": [_row("A")]})
