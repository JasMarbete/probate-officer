"""Checks on the showcase scenarios, so a change to a rule cannot quietly break the demo.

These read the real data/ folder and do not write to it.
"""

import json

import config
from officer import diagnose, rules, store


def _scenarios():
    return json.loads((config.DATA_DIR / "showcase.json").read_text(encoding="utf-8"))


def test_every_scenario_has_a_case_and_a_clean_copy():
    for scenario in _scenarios():
        assert store.load_case(scenario["case_id"]).case_id == scenario["case_id"]
        assert (config.GOLDEN_DIR / f"{scenario['case_id']}.json").exists()


def test_showcase_cases_are_not_in_the_eval_labels():
    with (config.GOLDEN_DIR / "expected.jsonl").open(encoding="utf-8") as handle:
        labelled = {json.loads(line)["case_id"] for line in handle if line.strip()}
    assert not labelled & {s["case_id"] for s in _scenarios()}


def test_deterministic_expectations_match_the_rules_engine():
    deterministic = {r["on_fail"]["stop_reason"] for r in rules.load_rules() if r["kind"] == "deterministic"}
    for scenario in _scenarios():
        case = store.load_case(scenario["case_id"], directory=config.GOLDEN_DIR)
        if case.state not in config.IN_SCOPE_STATES:
            continue
        found = {f.stop_reason for f in rules.run_deterministic(case) if not f.passed}
        expected = {r for r in scenario["expected"]["stop_reasons"] if r in deterministic}
        assert found == expected, scenario["case_id"]


def test_out_of_scope_scenario_is_refused_in_code():
    refused = [s for s in _scenarios() if s["expected"]["next_action"] == "refuse_out_of_scope"]
    assert refused
    for scenario in refused:
        assert diagnose.rules_only(scenario["case_id"]).next_action == "refuse_out_of_scope"
