"""Tests for officer/rules.py: every check type, the applicability filter, and full runs.

Each check gets at least one pass test and one fail test. Missing fields and
missing documents must count as a fail, never a crash.
"""

import pytest

import config
from officer import rules, store
from officer.models import Case


def _case_dict():
    # A valid case as a dict. Built fresh each time, so tests cannot share state.
    return {
        "case_id": "PRB-9100",
        "state": "issued",
        "application_type": "probate_will",
        "applicant": {"name": "Test Person A", "role": "executor", "address_given": True},
        "deceased": {"name": "Test Person B", "date_of_death": "2026-04-14", "domicile": "England and Wales"},
        "estate": {"gross_value": 1000, "net_value": 900, "iht_route": "excepted"},
        "documents": [
            {"type": "will", "received": True, "original": True, "text": None},
            {"type": "death_certificate", "received": True, "original": None, "text": None},
        ],
        "notes": [],
    }


def test_get_path_follows_dotted_path():
    assert rules.get_path(_case_dict(), "estate.gross_value") == 1000


def test_get_path_returns_none_when_missing():
    assert rules.get_path(_case_dict(), "estate.nonexistent.deep") is None


def test_get_doc_finds_first_match_or_none():
    case = _case_dict()
    assert rules.get_doc(case, "will")["original"] is True
    assert rules.get_doc(case, "codicil") is None


def test_field_present_pass_and_fail():
    case = _case_dict()
    assert rules.check_field_present(case, "estate.iht_route") is True
    case["estate"]["iht_route"] = None
    assert rules.check_field_present(case, "estate.iht_route") is False


def test_field_equals_pass_and_fail():
    case = _case_dict()
    assert rules.check_field_equals(case, "applicant.address_given", True) is True
    case["applicant"]["address_given"] = False
    assert rules.check_field_equals(case, "applicant.address_given", True) is False


def test_field_in_pass_and_fail():
    case = _case_dict()
    assert rules.check_field_in(case, "deceased.domicile", ["England and Wales"]) is True
    case["deceased"]["domicile"] = "Scotland"
    assert rules.check_field_in(case, "deceased.domicile", ["England and Wales"]) is False


def test_doc_received_pass_and_fail():
    case = _case_dict()
    assert rules.check_doc_received(case, "death_certificate") is True
    case["documents"][1]["received"] = False
    assert rules.check_doc_received(case, "death_certificate") is False


def test_doc_field_equals_pass_and_fail():
    case = _case_dict()
    assert rules.check_doc_field_equals(case, "will", "original", True) is True
    case["documents"][0]["original"] = False
    assert rules.check_doc_field_equals(case, "will", "original", True) is False


def test_number_compare_pass_and_fail():
    case = _case_dict()
    assert rules.check_number_compare(case, "estate.net_value", "<", 1000) is True
    assert rules.check_number_compare(case, "estate.net_value", ">=", 1000) is False


def test_fields_compare_pass_and_fail():
    case = _case_dict()
    assert rules.check_fields_compare(case, "estate.net_value", "<=", "estate.gross_value") is True
    case["estate"]["net_value"] = 2000
    assert rules.check_fields_compare(case, "estate.net_value", "<=", "estate.gross_value") is False


def test_date_not_future_pass_and_fail():
    case = _case_dict()
    assert rules.check_date_not_future(case, "deceased.date_of_death") is True
    case["deceased"]["date_of_death"] = "2999-01-01"
    assert rules.check_date_not_future(case, "deceased.date_of_death") is False


def test_missing_field_is_a_fail_not_a_crash():
    case = _case_dict()
    del case["estate"]
    assert rules.check_field_present(case, "estate.iht_route") is False
    assert rules.check_field_equals(case, "estate.iht_route", "excepted") is False
    assert rules.check_field_in(case, "estate.iht_route", ["excepted"]) is False
    assert rules.check_number_compare(case, "estate.net_value", "<", 5) is False
    assert rules.check_fields_compare(case, "estate.net_value", "<=", "estate.gross_value") is False
    assert rules.check_date_not_future(case, "deceased.date_of_death") is True


def test_missing_document_is_a_fail_not_a_crash():
    case = _case_dict()
    case["documents"] = []
    assert rules.check_doc_received(case, "death_certificate") is False
    assert rules.check_doc_field_equals(case, "will", "original", True) is False


def test_checks_registry_has_all_eight_types():
    assert set(rules.CHECKS) == {
        "field_present", "field_equals", "field_in", "doc_received",
        "doc_field_equals", "number_compare", "fields_compare", "date_not_future",
    }


def test_every_rule_in_rules_yaml_uses_a_known_check():
    for rule in rules.load_rules():
        if rule["kind"] == "deterministic":
            assert rule["check"] in rules.CHECKS, rule["id"]


def test_applicable_respects_application_type():
    rule = {"id": "R-X", "applies_to": ["probate_will"]}
    will_case = Case.model_validate(store.load_case("PRB-0001").model_dump() | {"application_type": "probate_will"})
    admin_case = Case.model_validate(store.load_case("PRB-0001").model_dump() | {"application_type": "letters_of_administration"})
    assert rules.applicable(rule, will_case) is True
    assert rules.applicable(rule, admin_case) is False
    assert rules.applicable({"id": "R-Y"}, admin_case) is True


def test_run_deterministic_clean_case_has_no_failures():
    findings = rules.run_deterministic(store.load_case("PRB-0001"))
    assert findings and all(f.passed for f in findings)


def test_run_deterministic_missing_death_certificate():
    failed = [f for f in rules.run_deterministic(store.load_case("PRB-0002")) if not f.passed]
    assert [(f.rule_id, f.stop_reason, f.action) for f in failed] == [
        ("R-DOC-01", "DEATH_CERT_MISSING", "request_document"),
    ]


def test_run_deterministic_copy_will():
    failed = [f for f in rules.run_deterministic(store.load_case("PRB-0003")) if not f.passed]
    assert [(f.rule_id, f.stop_reason) for f in failed] == [("R-WILL-01", "ORIGINAL_WILL_MISSING")]


def test_judgement_rules_for_probate_will_are_listed():
    ids = [rule["id"] for rule in rules.judgement_rules_for(store.load_case("PRB-0001"))]
    assert ids == ["R-WILL-05", "R-WILL-06", "R-WILL-07", "R-NAME-01"]
