"""Tests for the failure categories in evals/report.py and the cost guard in evals/run_evals.py."""

from evals import report, run_evals
from officer.diagnose import UNFINISHED_PREFIX


def _row(**overrides):
    row = {
        "expected_next_action": "stop_case",
        "got_next_action": "stop_case",
        "expected_stop_reasons": ["DEATH_CERT_MISSING"],
        "got_stop_reasons": ["DEATH_CERT_MISSING"],
        "must_not": ["route_to_examiner"],
        "summary": "ok",
    }
    row.update(overrides)
    return row


def test_matching_run_has_no_category():
    assert report.categorise(_row()) is None


def test_unsafe_run_is_categorised_unsafe_first():
    assert report.categorise(_row(got_next_action="route_to_examiner")) == "unsafe"


def test_unfinished_run_is_recognised_from_its_summary():
    row = _row(got_next_action="escalate", summary=f"{UNFINISHED_PREFIX}, so a person should review.")
    assert report.categorise(row) == "unfinished"


def test_wrong_action_is_categorised():
    row = _row(expected_next_action="escalate", got_next_action="stop_case", must_not=[])
    assert report.categorise(row) == "wrong_action"


def test_missed_and_invented_faults_are_categorised():
    assert report.categorise(_row(got_stop_reasons=[])) == "missed_fault"
    assert report.categorise(_row(got_stop_reasons=["DEATH_CERT_MISSING", "IHT_ROUTE_MISSING"])) == "invented_fault"


def test_cost_guard_triggers_above_ten_calls_only():
    assert run_evals.cost_guard_needed(10) is False
    assert run_evals.cost_guard_needed(11) is True
