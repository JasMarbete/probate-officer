"""Checks on the golden set: its split and bucket counts, and that its labels agree with the rules.

These read the real data/golden/ folder and do not write to it.
"""

import json
from collections import Counter

import config
from officer import rules, store


def _labels():
    with (config.GOLDEN_DIR / "expected.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_split_and_bucket_counts_match_spec_section_10():
    labels = _labels()
    assert Counter(label["split"] for label in labels) == {"dev": 8, "test": 12}
    assert Counter(label["bucket"] for label in labels) == {
        "clean": 5, "single_fault": 7, "multi_fault": 4, "escalation": 2, "out_of_scope": 1, "injection": 1,
    }


def test_deterministic_labels_match_the_rules_engine():
    deterministic = {r["on_fail"]["stop_reason"] for r in rules.load_rules() if r["kind"] == "deterministic"}
    for label in _labels():
        if label["bucket"] in ("out_of_scope",):
            continue
        case = store.load_case(label["case_id"], directory=config.GOLDEN_DIR)
        found = {f.stop_reason for f in rules.run_deterministic(case) if not f.passed}
        expected = {reason for reason in label["stop_reasons"] if reason in deterministic}
        assert found == expected, label["case_id"]


def test_faulty_cases_must_not_route_to_examiner():
    for label in _labels():
        if label["stop_reasons"]:
            assert "route_to_examiner" in label["must_not"], label["case_id"]
