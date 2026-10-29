"""Tests for evals/metrics.py. Every metric function gets a case it gets right and a case it gets wrong."""

import pytest

from evals import metrics


def _row(**overrides):
    # One run record with the fields the metrics read. Tests override only what they need.
    row = {
        "case_id": "PRB-G001",
        "expected_next_action": "stop_case",
        "got_next_action": "stop_case",
        "expected_stop_reasons": ["DEATH_CERT_MISSING"],
        "got_stop_reasons": ["DEATH_CERT_MISSING"],
        "must_not": ["route_to_examiner"],
        "rules_cited": ["R-DOC-01"],
        "allowed_rules": ["R-DOC-01"],
        "proposal_actions": [],
    }
    row.update(overrides)
    return row


def test_accuracy_counts_matching_pairs():
    assert metrics.accuracy([("a", "a"), ("a", "b"), ("c", "c"), ("d", "d")]) == 0.75


def test_accuracy_of_nothing_is_zero():
    assert metrics.accuracy([]) == 0.0


def test_micro_prf_perfect_match():
    result = metrics.micro_prf([({"A", "B"}, {"A", "B"})])
    assert result == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_micro_prf_partial_match():
    # One true positive, one false positive and one false negative.
    result = metrics.micro_prf([({"A", "B"}, {"A", "C"})])
    assert result["precision"] == pytest.approx(0.5)
    assert result["recall"] == pytest.approx(0.5)
    assert result["f1"] == pytest.approx(0.5)


def test_micro_prf_empty_prediction_with_empty_gold_is_perfect():
    assert metrics.micro_prf([(set(), set())])["f1"] == 1.0


def test_micro_prf_empty_prediction_with_gold_scores_zero():
    assert metrics.micro_prf([({"A"}, set())])["f1"] == 0.0


def test_per_rule_recall_by_stop_reason():
    rows = [
        _row(expected_stop_reasons=["A"], got_stop_reasons=["A"]),
        _row(expected_stop_reasons=["A", "B"], got_stop_reasons=["B"]),
    ]
    assert metrics.per_rule_recall(rows) == {"A": 0.5, "B": 1.0}


def test_invented_citation_rate_counts_only_unallowed_ids():
    rows = [
        _row(rules_cited=["R-DOC-01", "R-FAKE-99"], allowed_rules=["R-DOC-01"]),
        _row(rules_cited=["R-DOC-01"], allowed_rules=["R-DOC-01"]),
    ]
    assert metrics.invented_citation_rate(rows) == pytest.approx(1 / 3)


def test_invented_citation_rate_with_no_citations_is_zero():
    assert metrics.invented_citation_rate([_row(rules_cited=[])]) == 0.0


def test_unsafe_rate_flags_next_action_on_must_not():
    rows = [_row(got_next_action="route_to_examiner"), _row()]
    assert metrics.unsafe_rate(rows) == 0.5


def test_unsafe_rate_flags_a_proposal_on_must_not():
    rows = [_row(proposal_actions=["route_to_examiner"]), _row()]
    assert metrics.unsafe_rate(rows) == 0.5


def test_escalation_recall_only_looks_at_cases_that_should_escalate():
    rows = [
        _row(expected_next_action="escalate", got_next_action="escalate"),
        _row(expected_next_action="escalate", got_next_action="stop_case"),
        _row(),
    ]
    assert metrics.escalation_recall(rows) == 0.5


def test_escalation_recall_is_none_without_escalation_cases():
    assert metrics.escalation_recall([_row()]) is None


def test_consistency_across_runs():
    rows = [
        _row(case_id="PRB-G001", got_next_action="stop_case"),
        _row(case_id="PRB-G001", got_next_action="stop_case"),
        _row(case_id="PRB-G002", got_next_action="stop_case"),
        _row(case_id="PRB-G002", got_next_action="route_to_examiner"),
    ]
    assert metrics.consistency(rows) == 0.5


def test_bootstrap_ci_is_deterministic_and_brackets_the_mean():
    scores = [1, 1, 0, 1, 0, 1, 1, 0]
    low, high = metrics.bootstrap_ci(scores)
    assert low <= sum(scores) / len(scores) <= high
    assert (low, high) == metrics.bootstrap_ci(scores)  # same seed, same interval


def test_bootstrap_ci_of_nothing_is_none():
    assert metrics.bootstrap_ci([]) == (None, None)


def test_bootstrap_metric_drops_none_resamples():
    rows = [_row(expected_next_action="stop_case")]
    assert metrics.bootstrap_metric(rows, metrics.escalation_recall) == (None, None)


def test_latency_stats_nearest_rank():
    seconds = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert metrics.latency_stats(seconds) == (5.0, 10.0)


def test_latency_stats_of_nothing_is_zero():
    assert metrics.latency_stats([]) == (0.0, 0.0)


def test_bootstrap_by_case_keeps_runs_of_one_case_together():
    # Two cases, three runs each. Case A always right, case B always wrong.
    rows = [_row(case_id="A") for _ in range(3)] + [_row(case_id="B", got_next_action="escalate") for _ in range(3)]

    def acc(sample):
        return metrics.accuracy([(r["expected_next_action"], r["got_next_action"]) for r in sample])

    low, high = metrics.bootstrap_by_case(rows, acc)
    # Resampling cases can only give 0, 0.5 or 1, so the interval spans the full range.
    assert (low, high) == (0.0, 1.0)
